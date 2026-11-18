/**
 * Auto-generated from the EPUB runtime source snapshot.
 * Responsibility: Buffer/base64/ieee754 utilities used by binary payload handling.
 * Module IDs: 63, 64, 65, 66
 */
export const binaryHelperModules = {
  63: function (t, e, n) {
    "use strict";
    (function (t) {
      /*!
       * The buffer module from node.js, for the browser.
       *
       * @author   Feross Aboukhadijeh <http://feross.org>
       * @license  MIT
       */
      var i = n(64),
        r = n(65),
        s = n(66);
      function o() {
        return h.TYPED_ARRAY_SUPPORT ? 2147483647 : 1073741823;
      }
      function a(t, e) {
        if (o() < e) throw new RangeError("Invalid typed array length");
        return (
          h.TYPED_ARRAY_SUPPORT
            ? ((t = new Uint8Array(e)).__proto__ = h.prototype)
            : (null === t && (t = new h(e)), (t.length = e)),
          t
        );
      }
      function h(t, e, n) {
        if (!(h.TYPED_ARRAY_SUPPORT || this instanceof h))
          return new h(t, e, n);
        if ("number" == typeof t) {
          if ("string" == typeof e)
            throw new Error(
              "If encoding is specified then the first argument must be a string",
            );
          return c(this, t);
        }
        return l(this, t, e, n);
      }
      function l(t, e, n, i) {
        if ("number" == typeof e)
          throw new TypeError('"value" argument must not be a number');
        return "undefined" != typeof ArrayBuffer && e instanceof ArrayBuffer
          ? (function (t, e, n, i) {
              if ((e.byteLength, n < 0 || e.byteLength < n))
                throw new RangeError("'offset' is out of bounds");
              if (e.byteLength < n + (i || 0))
                throw new RangeError("'length' is out of bounds");
              e =
                void 0 === n && void 0 === i
                  ? new Uint8Array(e)
                  : void 0 === i
                    ? new Uint8Array(e, n)
                    : new Uint8Array(e, n, i);
              h.TYPED_ARRAY_SUPPORT
                ? ((t = e).__proto__ = h.prototype)
                : (t = d(t, e));
              return t;
            })(t, e, n, i)
          : "string" == typeof e
            ? (function (t, e, n) {
                ("string" == typeof n && "" !== n) || (n = "utf8");
                if (!h.isEncoding(n))
                  throw new TypeError(
                    '"encoding" must be a valid string encoding',
                  );
                var i = 0 | p(e, n),
                  r = (t = a(t, i)).write(e, n);
                r !== i && (t = t.slice(0, r));
                return t;
              })(t, e, n)
            : (function (t, e) {
                if (h.isBuffer(e)) {
                  var n = 0 | f(e.length);
                  return (0 === (t = a(t, n)).length || e.copy(t, 0, 0, n), t);
                }
                if (e) {
                  if (
                    ("undefined" != typeof ArrayBuffer &&
                      e.buffer instanceof ArrayBuffer) ||
                    "length" in e
                  )
                    return "number" != typeof e.length || (i = e.length) != i
                      ? a(t, 0)
                      : d(t, e);
                  if ("Buffer" === e.type && s(e.data)) return d(t, e.data);
                }
                var i;
                throw new TypeError(
                  "First argument must be a string, Buffer, ArrayBuffer, Array, or array-like object.",
                );
              })(t, e);
      }
      function u(t) {
        if ("number" != typeof t)
          throw new TypeError('"size" argument must be a number');
        if (t < 0) throw new RangeError('"size" argument must not be negative');
      }
      function c(t, e) {
        if ((u(e), (t = a(t, e < 0 ? 0 : 0 | f(e))), !h.TYPED_ARRAY_SUPPORT))
          for (var n = 0; n < e; ++n) t[n] = 0;
        return t;
      }
      function d(t, e) {
        var n = e.length < 0 ? 0 : 0 | f(e.length);
        t = a(t, n);
        for (var i = 0; i < n; i += 1) t[i] = 255 & e[i];
        return t;
      }
      function f(t) {
        if (t >= o())
          throw new RangeError(
            "Attempt to allocate Buffer larger than maximum size: 0x" +
              o().toString(16) +
              " bytes",
          );
        return 0 | t;
      }
      function p(t, e) {
        if (h.isBuffer(t)) return t.length;
        if (
          "undefined" != typeof ArrayBuffer &&
          "function" == typeof ArrayBuffer.isView &&
          (ArrayBuffer.isView(t) || t instanceof ArrayBuffer)
        )
          return t.byteLength;
        "string" != typeof t && (t = "" + t);
        var n = t.length;
        if (0 === n) return 0;
        for (var i = !1; ; )
          switch (e) {
            case "ascii":
            case "latin1":
            case "binary":
              return n;
            case "utf8":
            case "utf-8":
            case void 0:
              return F(t).length;
            case "ucs2":
            case "ucs-2":
            case "utf16le":
            case "utf-16le":
              return 2 * n;
            case "hex":
              return n >>> 1;
            case "base64":
              return U(t).length;
            default:
              if (i) return F(t).length;
              ((e = ("" + e).toLowerCase()), (i = !0));
          }
      }
      function g(t, e, n) {
        var i = !1;
        if (((void 0 === e || e < 0) && (e = 0), e > this.length)) return "";
        if (((void 0 === n || n > this.length) && (n = this.length), n <= 0))
          return "";
        if ((n >>>= 0) <= (e >>>= 0)) return "";
        for (t || (t = "utf8"); ; )
          switch (t) {
            case "hex":
              return N(this, e, n);
            case "utf8":
            case "utf-8":
              return C(this, e, n);
            case "ascii":
              return T(this, e, n);
            case "latin1":
            case "binary":
              return A(this, e, n);
            case "base64":
              return S(this, e, n);
            case "ucs2":
            case "ucs-2":
            case "utf16le":
            case "utf-16le":
              return O(this, e, n);
            default:
              if (i) throw new TypeError("Unknown encoding: " + t);
              ((t = (t + "").toLowerCase()), (i = !0));
          }
      }
      function m(t, e, n) {
        var i = t[e];
        ((t[e] = t[n]), (t[n] = i));
      }
      function v(t, e, n, i, r) {
        if (0 === t.length) return -1;
        if (
          ("string" == typeof n
            ? ((i = n), (n = 0))
            : n > 2147483647
              ? (n = 2147483647)
              : n < -2147483648 && (n = -2147483648),
          (n = +n),
          isNaN(n) && (n = r ? 0 : t.length - 1),
          n < 0 && (n = t.length + n),
          n >= t.length)
        ) {
          if (r) return -1;
          n = t.length - 1;
        } else if (n < 0) {
          if (!r) return -1;
          n = 0;
        }
        if (("string" == typeof e && (e = h.from(e, i)), h.isBuffer(e)))
          return 0 === e.length ? -1 : y(t, e, n, i, r);
        if ("number" == typeof e)
          return (
            (e &= 255),
            h.TYPED_ARRAY_SUPPORT &&
            "function" == typeof Uint8Array.prototype.indexOf
              ? r
                ? Uint8Array.prototype.indexOf.call(t, e, n)
                : Uint8Array.prototype.lastIndexOf.call(t, e, n)
              : y(t, [e], n, i, r)
          );
        throw new TypeError("val must be string, number or Buffer");
      }
      function y(t, e, n, i, r) {
        var s,
          o = 1,
          a = t.length,
          h = e.length;
        if (
          void 0 !== i &&
          ("ucs2" === (i = String(i).toLowerCase()) ||
            "ucs-2" === i ||
            "utf16le" === i ||
            "utf-16le" === i)
        ) {
          if (t.length < 2 || e.length < 2) return -1;
          ((o = 2), (a /= 2), (h /= 2), (n /= 2));
        }
        function l(t, e) {
          return 1 === o ? t[e] : t.readUInt16BE(e * o);
        }
        if (r) {
          var u = -1;
          for (s = n; s < a; s++)
            if (l(t, s) === l(e, -1 === u ? 0 : s - u)) {
              if ((-1 === u && (u = s), s - u + 1 === h)) return u * o;
            } else (-1 !== u && (s -= s - u), (u = -1));
        } else
          for (n + h > a && (n = a - h), s = n; s >= 0; s--) {
            for (var c = !0, d = 0; d < h; d++)
              if (l(t, s + d) !== l(e, d)) {
                c = !1;
                break;
              }
            if (c) return s;
          }
        return -1;
      }
      function b(t, e, n, i) {
        n = Number(n) || 0;
        var r = t.length - n;
        i ? (i = Number(i)) > r && (i = r) : (i = r);
        var s = e.length;
        if (s % 2 != 0) throw new TypeError("Invalid hex string");
        i > s / 2 && (i = s / 2);
        for (var o = 0; o < i; ++o) {
          var a = parseInt(e.substr(2 * o, 2), 16);
          if (isNaN(a)) return o;
          t[n + o] = a;
        }
        return o;
      }
      function w(t, e, n, i) {
        return q(F(e, t.length - n), t, n, i);
      }
      function x(t, e, n, i) {
        return q(
          (function (t) {
            for (var e = [], n = 0; n < t.length; ++n)
              e.push(255 & t.charCodeAt(n));
            return e;
          })(e),
          t,
          n,
          i,
        );
      }
      function _(t, e, n, i) {
        return x(t, e, n, i);
      }
      function E(t, e, n, i) {
        return q(U(e), t, n, i);
      }
      function k(t, e, n, i) {
        return q(
          (function (t, e) {
            for (
              var n, i, r, s = [], o = 0;
              o < t.length && !((e -= 2) < 0);
              ++o
            )
              ((n = t.charCodeAt(o)),
                (i = n >> 8),
                (r = n % 256),
                s.push(r),
                s.push(i));
            return s;
          })(e, t.length - n),
          t,
          n,
          i,
        );
      }
      function S(t, e, n) {
        return 0 === e && n === t.length
          ? i.fromByteArray(t)
          : i.fromByteArray(t.slice(e, n));
      }
      function C(t, e, n) {
        n = Math.min(t.length, n);
        for (var i = [], r = e; r < n; ) {
          var s,
            o,
            a,
            h,
            l = t[r],
            u = null,
            c = l > 239 ? 4 : l > 223 ? 3 : l > 191 ? 2 : 1;
          if (r + c <= n)
            switch (c) {
              case 1:
                l < 128 && (u = l);
                break;
              case 2:
                128 == (192 & (s = t[r + 1])) &&
                  (h = ((31 & l) << 6) | (63 & s)) > 127 &&
                  (u = h);
                break;
              case 3:
                ((s = t[r + 1]),
                  (o = t[r + 2]),
                  128 == (192 & s) &&
                    128 == (192 & o) &&
                    (h = ((15 & l) << 12) | ((63 & s) << 6) | (63 & o)) >
                      2047 &&
                    (h < 55296 || h > 57343) &&
                    (u = h));
                break;
              case 4:
                ((s = t[r + 1]),
                  (o = t[r + 2]),
                  (a = t[r + 3]),
                  128 == (192 & s) &&
                    128 == (192 & o) &&
                    128 == (192 & a) &&
                    (h =
                      ((15 & l) << 18) |
                      ((63 & s) << 12) |
                      ((63 & o) << 6) |
                      (63 & a)) > 65535 &&
                    h < 1114112 &&
                    (u = h));
            }
          (null === u
            ? ((u = 65533), (c = 1))
            : u > 65535 &&
              ((u -= 65536),
              i.push(((u >>> 10) & 1023) | 55296),
              (u = 56320 | (1023 & u))),
            i.push(u),
            (r += c));
        }
        return (function (t) {
          var e = t.length;
          if (e <= 4096) return String.fromCharCode.apply(String, t);
          var n = "",
            i = 0;
          for (; i < e; )
            n += String.fromCharCode.apply(String, t.slice(i, (i += 4096)));
          return n;
        })(i);
      }
      ((e.Buffer = h),
        (e.SlowBuffer = function (t) {
          +t != t && (t = 0);
          return h.alloc(+t);
        }),
        (e.INSPECT_MAX_BYTES = 50),
        (h.TYPED_ARRAY_SUPPORT =
          void 0 !== t.TYPED_ARRAY_SUPPORT
            ? t.TYPED_ARRAY_SUPPORT
            : (function () {
                try {
                  var t = new Uint8Array(1);
                  return (
                    (t.__proto__ = {
                      __proto__: Uint8Array.prototype,
                      foo: function () {
                        return 42;
                      },
                    }),
                    42 === t.foo() &&
                      "function" == typeof t.subarray &&
                      0 === t.subarray(1, 1).byteLength
                  );
                } catch (t) {
                  return !1;
                }
              })()),
        (e.kMaxLength = o()),
        (h.poolSize = 8192),
        (h._augment = function (t) {
          return ((t.__proto__ = h.prototype), t);
        }),
        (h.from = function (t, e, n) {
          return l(null, t, e, n);
        }),
        h.TYPED_ARRAY_SUPPORT &&
          ((h.prototype.__proto__ = Uint8Array.prototype),
          (h.__proto__ = Uint8Array),
          "undefined" != typeof Symbol &&
            Symbol.species &&
            h[Symbol.species] === h &&
            Object.defineProperty(h, Symbol.species, {
              value: null,
              configurable: !0,
            })),
        (h.alloc = function (t, e, n) {
          return (function (t, e, n, i) {
            return (
              u(e),
              e <= 0
                ? a(t, e)
                : void 0 !== n
                  ? "string" == typeof i
                    ? a(t, e).fill(n, i)
                    : a(t, e).fill(n)
                  : a(t, e)
            );
          })(null, t, e, n);
        }),
        (h.allocUnsafe = function (t) {
          return c(null, t);
        }),
        (h.allocUnsafeSlow = function (t) {
          return c(null, t);
        }),
        (h.isBuffer = function (t) {
          return !(null == t || !t._isBuffer);
        }),
        (h.compare = function (t, e) {
          if (!h.isBuffer(t) || !h.isBuffer(e))
            throw new TypeError("Arguments must be Buffers");
          if (t === e) return 0;
          for (
            var n = t.length, i = e.length, r = 0, s = Math.min(n, i);
            r < s;
            ++r
          )
            if (t[r] !== e[r]) {
              ((n = t[r]), (i = e[r]));
              break;
            }
          return n < i ? -1 : i < n ? 1 : 0;
        }),
        (h.isEncoding = function (t) {
          switch (String(t).toLowerCase()) {
            case "hex":
            case "utf8":
            case "utf-8":
            case "ascii":
            case "latin1":
            case "binary":
            case "base64":
            case "ucs2":
            case "ucs-2":
            case "utf16le":
            case "utf-16le":
              return !0;
            default:
              return !1;
          }
        }),
        (h.concat = function (t, e) {
          if (!s(t))
            throw new TypeError('"list" argument must be an Array of Buffers');
          if (0 === t.length) return h.alloc(0);
          var n;
          if (void 0 === e)
            for (e = 0, n = 0; n < t.length; ++n) e += t[n].length;
          var i = h.allocUnsafe(e),
            r = 0;
          for (n = 0; n < t.length; ++n) {
            var o = t[n];
            if (!h.isBuffer(o))
              throw new TypeError(
                '"list" argument must be an Array of Buffers',
              );
            (o.copy(i, r), (r += o.length));
          }
          return i;
        }),
        (h.byteLength = p),
        (h.prototype._isBuffer = !0),
        (h.prototype.swap16 = function () {
          var t = this.length;
          if (t % 2 != 0)
            throw new RangeError("Buffer size must be a multiple of 16-bits");
          for (var e = 0; e < t; e += 2) m(this, e, e + 1);
          return this;
        }),
        (h.prototype.swap32 = function () {
          var t = this.length;
          if (t % 4 != 0)
            throw new RangeError("Buffer size must be a multiple of 32-bits");
          for (var e = 0; e < t; e += 4)
            (m(this, e, e + 3), m(this, e + 1, e + 2));
          return this;
        }),
        (h.prototype.swap64 = function () {
          var t = this.length;
          if (t % 8 != 0)
            throw new RangeError("Buffer size must be a multiple of 64-bits");
          for (var e = 0; e < t; e += 8)
            (m(this, e, e + 7),
              m(this, e + 1, e + 6),
              m(this, e + 2, e + 5),
              m(this, e + 3, e + 4));
          return this;
        }),
        (h.prototype.toString = function () {
          var t = 0 | this.length;
          return 0 === t
            ? ""
            : 0 === arguments.length
              ? C(this, 0, t)
              : g.apply(this, arguments);
        }),
        (h.prototype.equals = function (t) {
          if (!h.isBuffer(t)) throw new TypeError("Argument must be a Buffer");
          return this === t || 0 === h.compare(this, t);
        }),
        (h.prototype.inspect = function () {
          var t = "",
            n = e.INSPECT_MAX_BYTES;
          return (
            this.length > 0 &&
              ((t = this.toString("hex", 0, n).match(/.{2}/g).join(" ")),
              this.length > n && (t += " ... ")),
            "<Buffer " + t + ">"
          );
        }),
        (h.prototype.compare = function (t, e, n, i, r) {
          if (!h.isBuffer(t)) throw new TypeError("Argument must be a Buffer");
          if (
            (void 0 === e && (e = 0),
            void 0 === n && (n = t ? t.length : 0),
            void 0 === i && (i = 0),
            void 0 === r && (r = this.length),
            e < 0 || n > t.length || i < 0 || r > this.length)
          )
            throw new RangeError("out of range index");
          if (i >= r && e >= n) return 0;
          if (i >= r) return -1;
          if (e >= n) return 1;
          if (this === t) return 0;
          for (
            var s = (r >>>= 0) - (i >>>= 0),
              o = (n >>>= 0) - (e >>>= 0),
              a = Math.min(s, o),
              l = this.slice(i, r),
              u = t.slice(e, n),
              c = 0;
            c < a;
            ++c
          )
            if (l[c] !== u[c]) {
              ((s = l[c]), (o = u[c]));
              break;
            }
          return s < o ? -1 : o < s ? 1 : 0;
        }),
        (h.prototype.includes = function (t, e, n) {
          return -1 !== this.indexOf(t, e, n);
        }),
        (h.prototype.indexOf = function (t, e, n) {
          return v(this, t, e, n, !0);
        }),
        (h.prototype.lastIndexOf = function (t, e, n) {
          return v(this, t, e, n, !1);
        }),
        (h.prototype.write = function (t, e, n, i) {
          if (void 0 === e) ((i = "utf8"), (n = this.length), (e = 0));
          else if (void 0 === n && "string" == typeof e)
            ((i = e), (n = this.length), (e = 0));
          else {
            if (!isFinite(e))
              throw new Error(
                "Buffer.write(string, encoding, offset[, length]) is no longer supported",
              );
            ((e |= 0),
              isFinite(n)
                ? ((n |= 0), void 0 === i && (i = "utf8"))
                : ((i = n), (n = void 0)));
          }
          var r = this.length - e;
          if (
            ((void 0 === n || n > r) && (n = r),
            (t.length > 0 && (n < 0 || e < 0)) || e > this.length)
          )
            throw new RangeError("Attempt to write outside buffer bounds");
          i || (i = "utf8");
          for (var s = !1; ; )
            switch (i) {
              case "hex":
                return b(this, t, e, n);
              case "utf8":
              case "utf-8":
                return w(this, t, e, n);
              case "ascii":
                return x(this, t, e, n);
              case "latin1":
              case "binary":
                return _(this, t, e, n);
              case "base64":
                return E(this, t, e, n);
              case "ucs2":
              case "ucs-2":
              case "utf16le":
              case "utf-16le":
                return k(this, t, e, n);
              default:
                if (s) throw new TypeError("Unknown encoding: " + i);
                ((i = ("" + i).toLowerCase()), (s = !0));
            }
        }),
        (h.prototype.toJSON = function () {
          return {
            type: "Buffer",
            data: Array.prototype.slice.call(this._arr || this, 0),
          };
        }));
      function T(t, e, n) {
        var i = "";
        n = Math.min(t.length, n);
        for (var r = e; r < n; ++r) i += String.fromCharCode(127 & t[r]);
        return i;
      }
      function A(t, e, n) {
        var i = "";
        n = Math.min(t.length, n);
        for (var r = e; r < n; ++r) i += String.fromCharCode(t[r]);
        return i;
      }
      function N(t, e, n) {
        var i = t.length;
        ((!e || e < 0) && (e = 0), (!n || n < 0 || n > i) && (n = i));
        for (var r = "", s = e; s < n; ++s) r += M(t[s]);
        return r;
      }
      function O(t, e, n) {
        for (var i = t.slice(e, n), r = "", s = 0; s < i.length; s += 2)
          r += String.fromCharCode(i[s] + 256 * i[s + 1]);
        return r;
      }
      function I(t, e, n) {
        if (t % 1 != 0 || t < 0) throw new RangeError("offset is not uint");
        if (t + e > n)
          throw new RangeError("Trying to access beyond buffer length");
      }
      function R(t, e, n, i, r, s) {
        if (!h.isBuffer(t))
          throw new TypeError('"buffer" argument must be a Buffer instance');
        if (e > r || e < s)
          throw new RangeError('"value" argument is out of bounds');
        if (n + i > t.length) throw new RangeError("Index out of range");
      }
      function D(t, e, n, i) {
        e < 0 && (e = 65535 + e + 1);
        for (var r = 0, s = Math.min(t.length - n, 2); r < s; ++r)
          t[n + r] =
            (e & (255 << (8 * (i ? r : 1 - r)))) >>> (8 * (i ? r : 1 - r));
      }
      function L(t, e, n, i) {
        e < 0 && (e = 4294967295 + e + 1);
        for (var r = 0, s = Math.min(t.length - n, 4); r < s; ++r)
          t[n + r] = (e >>> (8 * (i ? r : 3 - r))) & 255;
      }
      function j(t, e, n, i, r, s) {
        if (n + i > t.length) throw new RangeError("Index out of range");
        if (n < 0) throw new RangeError("Index out of range");
      }
      function z(t, e, n, i, s) {
        return (s || j(t, 0, n, 4), r.write(t, e, n, i, 23, 4), n + 4);
      }
      function P(t, e, n, i, s) {
        return (s || j(t, 0, n, 8), r.write(t, e, n, i, 52, 8), n + 8);
      }
      ((h.prototype.slice = function (t, e) {
        var n,
          i = this.length;
        if (
          ((t = ~~t) < 0 ? (t += i) < 0 && (t = 0) : t > i && (t = i),
          (e = void 0 === e ? i : ~~e) < 0
            ? (e += i) < 0 && (e = 0)
            : e > i && (e = i),
          e < t && (e = t),
          h.TYPED_ARRAY_SUPPORT)
        )
          (n = this.subarray(t, e)).__proto__ = h.prototype;
        else {
          var r = e - t;
          n = new h(r, void 0);
          for (var s = 0; s < r; ++s) n[s] = this[s + t];
        }
        return n;
      }),
        (h.prototype.readUIntLE = function (t, e, n) {
          ((t |= 0), (e |= 0), n || I(t, e, this.length));
          for (var i = this[t], r = 1, s = 0; ++s < e && (r *= 256); )
            i += this[t + s] * r;
          return i;
        }),
        (h.prototype.readUIntBE = function (t, e, n) {
          ((t |= 0), (e |= 0), n || I(t, e, this.length));
          for (var i = this[t + --e], r = 1; e > 0 && (r *= 256); )
            i += this[t + --e] * r;
          return i;
        }),
        (h.prototype.readUInt8 = function (t, e) {
          return (e || I(t, 1, this.length), this[t]);
        }),
        (h.prototype.readUInt16LE = function (t, e) {
          return (e || I(t, 2, this.length), this[t] | (this[t + 1] << 8));
        }),
        (h.prototype.readUInt16BE = function (t, e) {
          return (e || I(t, 2, this.length), (this[t] << 8) | this[t + 1]);
        }),
        (h.prototype.readUInt32LE = function (t, e) {
          return (
            e || I(t, 4, this.length),
            (this[t] | (this[t + 1] << 8) | (this[t + 2] << 16)) +
              16777216 * this[t + 3]
          );
        }),
        (h.prototype.readUInt32BE = function (t, e) {
          return (
            e || I(t, 4, this.length),
            16777216 * this[t] +
              ((this[t + 1] << 16) | (this[t + 2] << 8) | this[t + 3])
          );
        }),
        (h.prototype.readIntLE = function (t, e, n) {
          ((t |= 0), (e |= 0), n || I(t, e, this.length));
          for (var i = this[t], r = 1, s = 0; ++s < e && (r *= 256); )
            i += this[t + s] * r;
          return (i >= (r *= 128) && (i -= Math.pow(2, 8 * e)), i);
        }),
        (h.prototype.readIntBE = function (t, e, n) {
          ((t |= 0), (e |= 0), n || I(t, e, this.length));
          for (var i = e, r = 1, s = this[t + --i]; i > 0 && (r *= 256); )
            s += this[t + --i] * r;
          return (s >= (r *= 128) && (s -= Math.pow(2, 8 * e)), s);
        }),
        (h.prototype.readInt8 = function (t, e) {
          return (
            e || I(t, 1, this.length),
            128 & this[t] ? -1 * (255 - this[t] + 1) : this[t]
          );
        }),
        (h.prototype.readInt16LE = function (t, e) {
          e || I(t, 2, this.length);
          var n = this[t] | (this[t + 1] << 8);
          return 32768 & n ? 4294901760 | n : n;
        }),
        (h.prototype.readInt16BE = function (t, e) {
          e || I(t, 2, this.length);
          var n = this[t + 1] | (this[t] << 8);
          return 32768 & n ? 4294901760 | n : n;
        }),
        (h.prototype.readInt32LE = function (t, e) {
          return (
            e || I(t, 4, this.length),
            this[t] |
              (this[t + 1] << 8) |
              (this[t + 2] << 16) |
              (this[t + 3] << 24)
          );
        }),
        (h.prototype.readInt32BE = function (t, e) {
          return (
            e || I(t, 4, this.length),
            (this[t] << 24) |
              (this[t + 1] << 16) |
              (this[t + 2] << 8) |
              this[t + 3]
          );
        }),
        (h.prototype.readFloatLE = function (t, e) {
          return (e || I(t, 4, this.length), r.read(this, t, !0, 23, 4));
        }),
        (h.prototype.readFloatBE = function (t, e) {
          return (e || I(t, 4, this.length), r.read(this, t, !1, 23, 4));
        }),
        (h.prototype.readDoubleLE = function (t, e) {
          return (e || I(t, 8, this.length), r.read(this, t, !0, 52, 8));
        }),
        (h.prototype.readDoubleBE = function (t, e) {
          return (e || I(t, 8, this.length), r.read(this, t, !1, 52, 8));
        }),
        (h.prototype.writeUIntLE = function (t, e, n, i) {
          ((t = +t), (e |= 0), (n |= 0), i) ||
            R(this, t, e, n, Math.pow(2, 8 * n) - 1, 0);
          var r = 1,
            s = 0;
          for (this[e] = 255 & t; ++s < n && (r *= 256); )
            this[e + s] = (t / r) & 255;
          return e + n;
        }),
        (h.prototype.writeUIntBE = function (t, e, n, i) {
          ((t = +t), (e |= 0), (n |= 0), i) ||
            R(this, t, e, n, Math.pow(2, 8 * n) - 1, 0);
          var r = n - 1,
            s = 1;
          for (this[e + r] = 255 & t; --r >= 0 && (s *= 256); )
            this[e + r] = (t / s) & 255;
          return e + n;
        }),
        (h.prototype.writeUInt8 = function (t, e, n) {
          return (
            (t = +t),
            (e |= 0),
            n || R(this, t, e, 1, 255, 0),
            h.TYPED_ARRAY_SUPPORT || (t = Math.floor(t)),
            (this[e] = 255 & t),
            e + 1
          );
        }),
        (h.prototype.writeUInt16LE = function (t, e, n) {
          return (
            (t = +t),
            (e |= 0),
            n || R(this, t, e, 2, 65535, 0),
            h.TYPED_ARRAY_SUPPORT
              ? ((this[e] = 255 & t), (this[e + 1] = t >>> 8))
              : D(this, t, e, !0),
            e + 2
          );
        }),
        (h.prototype.writeUInt16BE = function (t, e, n) {
          return (
            (t = +t),
            (e |= 0),
            n || R(this, t, e, 2, 65535, 0),
            h.TYPED_ARRAY_SUPPORT
              ? ((this[e] = t >>> 8), (this[e + 1] = 255 & t))
              : D(this, t, e, !1),
            e + 2
          );
        }),
        (h.prototype.writeUInt32LE = function (t, e, n) {
          return (
            (t = +t),
            (e |= 0),
            n || R(this, t, e, 4, 4294967295, 0),
            h.TYPED_ARRAY_SUPPORT
              ? ((this[e + 3] = t >>> 24),
                (this[e + 2] = t >>> 16),
                (this[e + 1] = t >>> 8),
                (this[e] = 255 & t))
              : L(this, t, e, !0),
            e + 4
          );
        }),
        (h.prototype.writeUInt32BE = function (t, e, n) {
          return (
            (t = +t),
            (e |= 0),
            n || R(this, t, e, 4, 4294967295, 0),
            h.TYPED_ARRAY_SUPPORT
              ? ((this[e] = t >>> 24),
                (this[e + 1] = t >>> 16),
                (this[e + 2] = t >>> 8),
                (this[e + 3] = 255 & t))
              : L(this, t, e, !1),
            e + 4
          );
        }),
        (h.prototype.writeIntLE = function (t, e, n, i) {
          if (((t = +t), (e |= 0), !i)) {
            var r = Math.pow(2, 8 * n - 1);
            R(this, t, e, n, r - 1, -r);
          }
          var s = 0,
            o = 1,
            a = 0;
          for (this[e] = 255 & t; ++s < n && (o *= 256); )
            (t < 0 && 0 === a && 0 !== this[e + s - 1] && (a = 1),
              (this[e + s] = (((t / o) >> 0) - a) & 255));
          return e + n;
        }),
        (h.prototype.writeIntBE = function (t, e, n, i) {
          if (((t = +t), (e |= 0), !i)) {
            var r = Math.pow(2, 8 * n - 1);
            R(this, t, e, n, r - 1, -r);
          }
          var s = n - 1,
            o = 1,
            a = 0;
          for (this[e + s] = 255 & t; --s >= 0 && (o *= 256); )
            (t < 0 && 0 === a && 0 !== this[e + s + 1] && (a = 1),
              (this[e + s] = (((t / o) >> 0) - a) & 255));
          return e + n;
        }),
        (h.prototype.writeInt8 = function (t, e, n) {
          return (
            (t = +t),
            (e |= 0),
            n || R(this, t, e, 1, 127, -128),
            h.TYPED_ARRAY_SUPPORT || (t = Math.floor(t)),
            t < 0 && (t = 255 + t + 1),
            (this[e] = 255 & t),
            e + 1
          );
        }),
        (h.prototype.writeInt16LE = function (t, e, n) {
          return (
            (t = +t),
            (e |= 0),
            n || R(this, t, e, 2, 32767, -32768),
            h.TYPED_ARRAY_SUPPORT
              ? ((this[e] = 255 & t), (this[e + 1] = t >>> 8))
              : D(this, t, e, !0),
            e + 2
          );
        }),
        (h.prototype.writeInt16BE = function (t, e, n) {
          return (
            (t = +t),
            (e |= 0),
            n || R(this, t, e, 2, 32767, -32768),
            h.TYPED_ARRAY_SUPPORT
              ? ((this[e] = t >>> 8), (this[e + 1] = 255 & t))
              : D(this, t, e, !1),
            e + 2
          );
        }),
        (h.prototype.writeInt32LE = function (t, e, n) {
          return (
            (t = +t),
            (e |= 0),
            n || R(this, t, e, 4, 2147483647, -2147483648),
            h.TYPED_ARRAY_SUPPORT
              ? ((this[e] = 255 & t),
                (this[e + 1] = t >>> 8),
                (this[e + 2] = t >>> 16),
                (this[e + 3] = t >>> 24))
              : L(this, t, e, !0),
            e + 4
          );
        }),
        (h.prototype.writeInt32BE = function (t, e, n) {
          return (
            (t = +t),
            (e |= 0),
            n || R(this, t, e, 4, 2147483647, -2147483648),
            t < 0 && (t = 4294967295 + t + 1),
            h.TYPED_ARRAY_SUPPORT
              ? ((this[e] = t >>> 24),
                (this[e + 1] = t >>> 16),
                (this[e + 2] = t >>> 8),
                (this[e + 3] = 255 & t))
              : L(this, t, e, !1),
            e + 4
          );
        }),
        (h.prototype.writeFloatLE = function (t, e, n) {
          return z(this, t, e, !0, n);
        }),
        (h.prototype.writeFloatBE = function (t, e, n) {
          return z(this, t, e, !1, n);
        }),
        (h.prototype.writeDoubleLE = function (t, e, n) {
          return P(this, t, e, !0, n);
        }),
        (h.prototype.writeDoubleBE = function (t, e, n) {
          return P(this, t, e, !1, n);
        }),
        (h.prototype.copy = function (t, e, n, i) {
          if (
            (n || (n = 0),
            i || 0 === i || (i = this.length),
            e >= t.length && (e = t.length),
            e || (e = 0),
            i > 0 && i < n && (i = n),
            i === n)
          )
            return 0;
          if (0 === t.length || 0 === this.length) return 0;
          if (e < 0) throw new RangeError("targetStart out of bounds");
          if (n < 0 || n >= this.length)
            throw new RangeError("sourceStart out of bounds");
          if (i < 0) throw new RangeError("sourceEnd out of bounds");
          (i > this.length && (i = this.length),
            t.length - e < i - n && (i = t.length - e + n));
          var r,
            s = i - n;
          if (this === t && n < e && e < i)
            for (r = s - 1; r >= 0; --r) t[r + e] = this[r + n];
          else if (s < 1e3 || !h.TYPED_ARRAY_SUPPORT)
            for (r = 0; r < s; ++r) t[r + e] = this[r + n];
          else Uint8Array.prototype.set.call(t, this.subarray(n, n + s), e);
          return s;
        }),
        (h.prototype.fill = function (t, e, n, i) {
          if ("string" == typeof t) {
            if (
              ("string" == typeof e
                ? ((i = e), (e = 0), (n = this.length))
                : "string" == typeof n && ((i = n), (n = this.length)),
              1 === t.length)
            ) {
              var r = t.charCodeAt(0);
              r < 256 && (t = r);
            }
            if (void 0 !== i && "string" != typeof i)
              throw new TypeError("encoding must be a string");
            if ("string" == typeof i && !h.isEncoding(i))
              throw new TypeError("Unknown encoding: " + i);
          } else "number" == typeof t && (t &= 255);
          if (e < 0 || this.length < e || this.length < n)
            throw new RangeError("Out of range index");
          if (n <= e) return this;
          var s;
          if (
            ((e >>>= 0),
            (n = void 0 === n ? this.length : n >>> 0),
            t || (t = 0),
            "number" == typeof t)
          )
            for (s = e; s < n; ++s) this[s] = t;
          else {
            var o = h.isBuffer(t) ? t : F(new h(t, i).toString()),
              a = o.length;
            for (s = 0; s < n - e; ++s) this[s + e] = o[s % a];
          }
          return this;
        }));
      var B = /[^+\/0-9A-Za-z-_]/g;
      function M(t) {
        return t < 16 ? "0" + t.toString(16) : t.toString(16);
      }
      function F(t, e) {
        var n;
        e = e || 1 / 0;
        for (var i = t.length, r = null, s = [], o = 0; o < i; ++o) {
          if ((n = t.charCodeAt(o)) > 55295 && n < 57344) {
            if (!r) {
              if (n > 56319) {
                (e -= 3) > -1 && s.push(239, 191, 189);
                continue;
              }
              if (o + 1 === i) {
                (e -= 3) > -1 && s.push(239, 191, 189);
                continue;
              }
              r = n;
              continue;
            }
            if (n < 56320) {
              ((e -= 3) > -1 && s.push(239, 191, 189), (r = n));
              continue;
            }
            n = 65536 + (((r - 55296) << 10) | (n - 56320));
          } else r && (e -= 3) > -1 && s.push(239, 191, 189);
          if (((r = null), n < 128)) {
            if ((e -= 1) < 0) break;
            s.push(n);
          } else if (n < 2048) {
            if ((e -= 2) < 0) break;
            s.push((n >> 6) | 192, (63 & n) | 128);
          } else if (n < 65536) {
            if ((e -= 3) < 0) break;
            s.push((n >> 12) | 224, ((n >> 6) & 63) | 128, (63 & n) | 128);
          } else {
            if (!(n < 1114112)) throw new Error("Invalid code point");
            if ((e -= 4) < 0) break;
            s.push(
              (n >> 18) | 240,
              ((n >> 12) & 63) | 128,
              ((n >> 6) & 63) | 128,
              (63 & n) | 128,
            );
          }
        }
        return s;
      }
      function U(t) {
        return i.toByteArray(
          (function (t) {
            if (
              (t = (function (t) {
                return t.trim ? t.trim() : t.replace(/^\s+|\s+$/g, "");
              })(t).replace(B, "")).length < 2
            )
              return "";
            for (; t.length % 4 != 0; ) t += "=";
            return t;
          })(t),
        );
      }
      function q(t, e, n, i) {
        for (var r = 0; r < i && !(r + n >= e.length || r >= t.length); ++r)
          e[r + n] = t[r];
        return r;
      }
    }).call(this, n(9));
  },
  64: function (t, e, n) {
    "use strict";
    ((e.byteLength = function (t) {
      var e = l(t),
        n = e[0],
        i = e[1];
      return (3 * (n + i)) / 4 - i;
    }),
      (e.toByteArray = function (t) {
        var e,
          n,
          i = l(t),
          o = i[0],
          a = i[1],
          h = new s(
            (function (t, e, n) {
              return (3 * (e + n)) / 4 - n;
            })(0, o, a),
          ),
          u = 0,
          c = a > 0 ? o - 4 : o;
        for (n = 0; n < c; n += 4)
          ((e =
            (r[t.charCodeAt(n)] << 18) |
            (r[t.charCodeAt(n + 1)] << 12) |
            (r[t.charCodeAt(n + 2)] << 6) |
            r[t.charCodeAt(n + 3)]),
            (h[u++] = (e >> 16) & 255),
            (h[u++] = (e >> 8) & 255),
            (h[u++] = 255 & e));
        2 === a &&
          ((e = (r[t.charCodeAt(n)] << 2) | (r[t.charCodeAt(n + 1)] >> 4)),
          (h[u++] = 255 & e));
        1 === a &&
          ((e =
            (r[t.charCodeAt(n)] << 10) |
            (r[t.charCodeAt(n + 1)] << 4) |
            (r[t.charCodeAt(n + 2)] >> 2)),
          (h[u++] = (e >> 8) & 255),
          (h[u++] = 255 & e));
        return h;
      }),
      (e.fromByteArray = function (t) {
        for (
          var e, n = t.length, r = n % 3, s = [], o = 0, a = n - r;
          o < a;
          o += 16383
        )
          s.push(u(t, o, o + 16383 > a ? a : o + 16383));
        1 === r
          ? ((e = t[n - 1]), s.push(i[e >> 2] + i[(e << 4) & 63] + "=="))
          : 2 === r &&
            ((e = (t[n - 2] << 8) + t[n - 1]),
            s.push(i[e >> 10] + i[(e >> 4) & 63] + i[(e << 2) & 63] + "="));
        return s.join("");
      }));
    for (
      var i = [],
        r = [],
        s = "undefined" != typeof Uint8Array ? Uint8Array : Array,
        o = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",
        a = 0,
        h = o.length;
      a < h;
      ++a
    )
      ((i[a] = o[a]), (r[o.charCodeAt(a)] = a));
    function l(t) {
      var e = t.length;
      if (e % 4 > 0)
        throw new Error("Invalid string. Length must be a multiple of 4");
      var n = t.indexOf("=");
      return (-1 === n && (n = e), [n, n === e ? 0 : 4 - (n % 4)]);
    }
    function u(t, e, n) {
      for (var r, s, o = [], a = e; a < n; a += 3)
        ((r =
          ((t[a] << 16) & 16711680) +
          ((t[a + 1] << 8) & 65280) +
          (255 & t[a + 2])),
          o.push(
            i[((s = r) >> 18) & 63] +
              i[(s >> 12) & 63] +
              i[(s >> 6) & 63] +
              i[63 & s],
          ));
      return o.join("");
    }
    ((r["-".charCodeAt(0)] = 62), (r["_".charCodeAt(0)] = 63));
  },
  65: function (t, e) {
    /*! ieee754. BSD-3-Clause License. Feross Aboukhadijeh <https://feross.org/opensource> */
    ((e.read = function (t, e, n, i, r) {
      var s,
        o,
        a = 8 * r - i - 1,
        h = (1 << a) - 1,
        l = h >> 1,
        u = -7,
        c = n ? r - 1 : 0,
        d = n ? -1 : 1,
        f = t[e + c];
      for (
        c += d, s = f & ((1 << -u) - 1), f >>= -u, u += a;
        u > 0;
        s = 256 * s + t[e + c], c += d, u -= 8
      );
      for (
        o = s & ((1 << -u) - 1), s >>= -u, u += i;
        u > 0;
        o = 256 * o + t[e + c], c += d, u -= 8
      );
      if (0 === s) s = 1 - l;
      else {
        if (s === h) return o ? NaN : (1 / 0) * (f ? -1 : 1);
        ((o += Math.pow(2, i)), (s -= l));
      }
      return (f ? -1 : 1) * o * Math.pow(2, s - i);
    }),
      (e.write = function (t, e, n, i, r, s) {
        var o,
          a,
          h,
          l = 8 * s - r - 1,
          u = (1 << l) - 1,
          c = u >> 1,
          d = 23 === r ? Math.pow(2, -24) - Math.pow(2, -77) : 0,
          f = i ? 0 : s - 1,
          p = i ? 1 : -1,
          g = e < 0 || (0 === e && 1 / e < 0) ? 1 : 0;
        for (
          e = Math.abs(e),
            isNaN(e) || e === 1 / 0
              ? ((a = isNaN(e) ? 1 : 0), (o = u))
              : ((o = Math.floor(Math.log(e) / Math.LN2)),
                e * (h = Math.pow(2, -o)) < 1 && (o--, (h *= 2)),
                (e += o + c >= 1 ? d / h : d * Math.pow(2, 1 - c)) * h >= 2 &&
                  (o++, (h /= 2)),
                o + c >= u
                  ? ((a = 0), (o = u))
                  : o + c >= 1
                    ? ((a = (e * h - 1) * Math.pow(2, r)), (o += c))
                    : ((a = e * Math.pow(2, c - 1) * Math.pow(2, r)), (o = 0)));
          r >= 8;
          t[n + f] = 255 & a, f += p, a /= 256, r -= 8
        );
        for (
          o = (o << r) | a, l += r;
          l > 0;
          t[n + f] = 255 & o, f += p, o /= 256, l -= 8
        );
        t[n + f - p] |= 128 * g;
      }));
  },
  66: function (t, e) {
    var n = {}.toString;
    t.exports =
      Array.isArray ||
      function (t) {
        return "[object Array]" == n.call(t);
      };
  },
};
