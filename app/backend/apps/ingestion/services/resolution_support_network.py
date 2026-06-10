import socket
import struct
from ipaddress import ip_address
from random import randint
from urllib.parse import urlencode, urlparse

import requests
import urllib3
from requests.structures import CaseInsensitiveDict

from apps.ingestion.services.resolution_support_hosts import (
    SEARCH_HEADERS,
    get_source_site_dns_resolvers,
    is_name_resolution_failure,
    replace_url_host,
    source_request_hosts,
)


def collect_system_dns_ips(host):
    ips = []
    try:
        addr_info = socket.getaddrinfo(
            host,
            443,
            socket.AF_UNSPEC,
            socket.SOCK_STREAM,
        )
    except OSError:
        return ips

    seen = set()
    for family, _socktype, _proto, _canon, sockaddr in addr_info:
        if family not in (socket.AF_INET, socket.AF_INET6) or not sockaddr:
            continue
        candidate = str(sockaddr[0]).strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        ips.append(candidate)
    return ips


def encode_dns_name(name):
    labels = [label for label in name.split(".") if label]
    wire = b""
    for label in labels:
        encoded = label.encode("idna")
        wire += bytes((len(encoded),)) + encoded
    return wire + b"\x00"


def skip_dns_name(packet, offset):
    while offset < len(packet):
        length = packet[offset]
        if length == 0:
            return offset + 1
        if (length & 0xC0) == 0xC0:
            return offset + 2
        offset += 1 + length
    return offset


def resolve_a_records_via_udp(host, resolver, timeout=3):
    transaction_id = randint(0, 0xFFFF)
    header = struct.pack("!HHHHHH", transaction_id, 0x0100, 1, 0, 0, 0)
    question = encode_dns_name(host) + struct.pack("!HH", 1, 1)
    query = header + question

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        sock.sendto(query, (resolver, 53))
        packet, _ = sock.recvfrom(2048)

    if len(packet) < 12:
        return []

    resp_tx_id, _flags, qdcount, ancount, _nscount, _arcount = struct.unpack(
        "!HHHHHH",
        packet[:12],
    )
    if resp_tx_id != transaction_id:
        return []

    offset = 12
    for _ in range(qdcount):
        offset = skip_dns_name(packet, offset)
        offset += 4

    ips = []
    seen = set()
    for _ in range(ancount):
        offset = skip_dns_name(packet, offset)
        if offset + 10 > len(packet):
            break

        rtype, _rclass, _ttl, rdlength = struct.unpack("!HHIH", packet[offset : offset + 10])
        offset += 10
        if offset + rdlength > len(packet):
            break

        rdata = packet[offset : offset + rdlength]
        offset += rdlength
        if rtype != 1 or rdlength != 4:
            continue
        try:
            ip_value = socket.inet_ntoa(rdata)
            ip_address(ip_value)
        except ValueError:
            continue
        if ip_value in seen:
            continue
        seen.add(ip_value)
        ips.append(ip_value)

    return ips


def resolve_a_records_via_doh(host, timeout=5):
    try:
        response = requests.get(
            "https://1.1.1.1/dns-query",
            params={"name": host, "type": "A"},
            headers={
                "Accept": "application/dns-json",
                "Host": "cloudflare-dns.com",
                "User-Agent": SEARCH_HEADERS["User-Agent"],
            },
            timeout=timeout,
            verify=False,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return []

    answers = payload.get("Answer", []) if isinstance(payload, dict) else []
    ips = []
    seen = set()
    for answer in answers:
        if not isinstance(answer, dict) or answer.get("type") != 1:
            continue
        value = str(answer.get("data", "")).strip()
        if not value:
            continue
        try:
            ip_address(value)
        except ValueError:
            continue
        if value in seen:
            continue
        seen.add(value)
        ips.append(value)

    return ips


def resolve_host_with_dns_fallback(host):
    collected = []
    seen = set()

    for candidate in collect_system_dns_ips(host):
        if candidate in seen:
            continue
        seen.add(candidate)
        collected.append(candidate)

    for resolver in get_source_site_dns_resolvers():
        try:
            udp_ips = resolve_a_records_via_udp(host, resolver)
        except Exception:
            udp_ips = []
        for candidate in udp_ips:
            if candidate in seen:
                continue
            seen.add(candidate)
            collected.append(candidate)

    if collected:
        return collected

    for candidate in resolve_a_records_via_doh(host):
        if candidate in seen:
            continue
        seen.add(candidate)
        collected.append(candidate)

    return collected


def build_response_from_urllib3(url, method, headers, raw_response):
    response = requests.Response()
    response.status_code = raw_response.status
    response.headers = CaseInsensitiveDict(raw_response.headers)
    response._content = raw_response.data
    response.url = url
    response.reason = getattr(raw_response, "reason", "")
    response.encoding = requests.utils.get_encoding_from_headers(response.headers)
    response.request = requests.Request(method=method, url=url, headers=headers).prepare()
    return response


def get_via_direct_ip_https(session, url, host, ip, **kwargs):
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        raise requests.exceptions.ConnectionError(f"Direct-IP fallback requires HTTPS URL: {url}")

    params = kwargs.get("params")
    timeout = kwargs.get("timeout", 30)
    method = kwargs.get("method", "GET").upper()
    allow_redirects = kwargs.get("allow_redirects", True)
    provided_headers = kwargs.get("headers") or {}

    base_path = parsed.path or "/"
    query = parsed.query
    if params:
        params_query = urlencode(params, doseq=True)
        if params_query:
            query = f"{query}&{params_query}" if query else params_query
    request_target = f"{base_path}?{query}" if query else base_path

    merged_headers = {}
    merged_headers.update(getattr(session, "headers", {}) or {})
    merged_headers.update(provided_headers)
    merged_headers["Host"] = host

    pool = urllib3.HTTPSConnectionPool(
        host=ip,
        port=parsed.port or 443,
        assert_hostname=host,
        server_hostname=host,
        cert_reqs="CERT_REQUIRED",
        ca_certs=requests.certs.where(),
        retries=False,
        timeout=timeout,
    )
    raw_response = pool.request(method, request_target, headers=merged_headers, redirect=allow_redirects)
    return build_response_from_urllib3(url, method, merged_headers, raw_response)


def get_with_host_fallback(session, url, **kwargs):
    parsed = urlparse(url)
    candidate_hosts = source_request_hosts(parsed.netloc)
    candidate_urls = [replace_url_host(url, host) for host in candidate_hosts]
    fallback_errors = []

    for candidate_url in candidate_urls:
        try:
            return session.get(candidate_url, **kwargs)
        except requests.exceptions.ConnectionError as exc:
            if not is_name_resolution_failure(exc):
                raise
            fallback_errors.append(exc)

    direct_ip_errors = []
    for host in candidate_hosts:
        candidate_url = replace_url_host(url, host)
        for resolved_ip in resolve_host_with_dns_fallback(host):
            try:
                return get_via_direct_ip_https(session, candidate_url, host, resolved_ip, **kwargs)
            except requests.exceptions.RequestException as exc:
                direct_ip_errors.append(exc)

    if direct_ip_errors:
        raise direct_ip_errors[-1]
    if fallback_errors:
        raise fallback_errors[-1]
    return session.get(url, **kwargs)

