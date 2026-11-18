/**
 * Auto-generated from the EPUB runtime source snapshot.
 * Responsibility: CFI parsing, navigation parsing, and XML entity/name helpers.
 * Module IDs: 18, 51, 52
 */
export const contentParserModules = {
  18: function (t, e, n) {
    function i(t) {
      this.options = t || {
        locator: {},
      };
    }
    function r() {
      this.cdata = !1;
    }
    function s(t, e) {
      ((e.lineNumber = t.lineNumber), (e.columnNumber = t.columnNumber));
    }
    function o(t) {
      if (t)
        return (
          "\n@" +
          (t.systemId || "") +
          "#[line:" +
          t.lineNumber +
          ",col:" +
          t.columnNumber +
          "]"
        );
    }
    function a(t, e, n) {
      return "string" == typeof t
        ? t.substr(e, n)
        : t.length >= e + n || e
          ? new java.lang.String(t, e, n) + ""
          : t;
    }
    function h(t, e) {
      t.currentElement ? t.currentElement.appendChild(e) : t.doc.appendChild(e);
    }
    ((i.prototype.parseFromString = function (t, e) {
      var n = this.options,
        i = new u(),
        s = n.domBuilder || new r(),
        a = n.errorHandler,
        h = n.locator,
        c = n.xmlns || {},
        d = /\/x?html?$/.test(e),
        f = d
          ? l.entityMap
          : {
              lt: "<",
              gt: ">",
              amp: "&",
              quot: '"',
              apos: "'",
            };
      return (
        h && s.setDocumentLocator(h),
        (i.errorHandler = (function (t, e, n) {
          if (!t) {
            if (e instanceof r) return e;
            t = e;
          }
          var i = {},
            s = t instanceof Function;
          function a(e) {
            var r = t[e];
            (!r &&
              s &&
              (r =
                2 == t.length
                  ? function (n) {
                      t(e, n);
                    }
                  : t),
              (i[e] =
                (r &&
                  function (t) {
                    r("[xmldom " + e + "]\t" + t + o(n));
                  }) ||
                function () {}));
          }
          return ((n = n || {}), a("warning"), a("error"), a("fatalError"), i);
        })(a, s, h)),
        (i.domBuilder = n.domBuilder || s),
        d && (c[""] = "http://www.w3.org/1999/xhtml"),
        (c.xml = c.xml || "http://www.w3.org/XML/1998/namespace"),
        t ? i.parse(t, c, f) : i.errorHandler.error("invalid doc source"),
        s.doc
      );
    }),
      (r.prototype = {
        startDocument: function () {
          ((this.doc = new c().createDocument(null, null, null)),
            this.locator && (this.doc.documentURI = this.locator.systemId));
        },
        startElement: function (t, e, n, i) {
          var r = this.doc,
            o = r.createElementNS(t, n || e),
            a = i.length;
          (h(this, o),
            (this.currentElement = o),
            this.locator && s(this.locator, o));
          for (var l = 0; l < a; l++) {
            t = i.getURI(l);
            var u = i.getValue(l),
              c = ((n = i.getQName(l)), r.createAttributeNS(t, n));
            (this.locator && s(i.getLocator(l), c),
              (c.value = c.nodeValue = u),
              o.setAttributeNode(c));
          }
        },
        endElement: function (t, e, n) {
          var i = this.currentElement;
          i.tagName;
          this.currentElement = i.parentNode;
        },
        startPrefixMapping: function (t, e) {},
        endPrefixMapping: function (t) {},
        processingInstruction: function (t, e) {
          var n = this.doc.createProcessingInstruction(t, e);
          (this.locator && s(this.locator, n), h(this, n));
        },
        ignorableWhitespace: function (t, e, n) {},
        characters: function (t, e, n) {
          if ((t = a.apply(this, arguments))) {
            if (this.cdata) var i = this.doc.createCDATASection(t);
            else i = this.doc.createTextNode(t);
            (this.currentElement
              ? this.currentElement.appendChild(i)
              : /^\s*$/.test(t) && this.doc.appendChild(i),
              this.locator && s(this.locator, i));
          }
        },
        skippedEntity: function (t) {},
        endDocument: function () {
          this.doc.normalize();
        },
        setDocumentLocator: function (t) {
          (this.locator = t) && (t.lineNumber = 0);
        },
        comment: function (t, e, n) {
          t = a.apply(this, arguments);
          var i = this.doc.createComment(t);
          (this.locator && s(this.locator, i), h(this, i));
        },
        startCDATA: function () {
          this.cdata = !0;
        },
        endCDATA: function () {
          this.cdata = !1;
        },
        startDTD: function (t, e, n) {
          var i = this.doc.implementation;
          if (i && i.createDocumentType) {
            var r = i.createDocumentType(t, e, n);
            (this.locator && s(this.locator, r), h(this, r));
          }
        },
        warning: function (t) {
          console.warn("[xmldom warning]\t" + t, o(this.locator));
        },
        error: function (t) {
          console.error("[xmldom error]\t" + t, o(this.locator));
        },
        fatalError: function (t) {
          throw (
            console.error("[xmldom fatalError]\t" + t, o(this.locator)),
            t
          );
        },
      }),
      "endDTD,startEntity,endEntity,attributeDecl,elementDecl,externalEntityDecl,internalEntityDecl,resolveEntity,getExternalSubset,notationDecl,unparsedEntityDecl".replace(
        /\w+/g,
        function (t) {
          r.prototype[t] = function () {
            return null;
          };
        },
      ));
    var l = n(51),
      u = n(52).XMLReader,
      c = (e.DOMImplementation = n(26).DOMImplementation);
    ((e.XMLSerializer = n(26).XMLSerializer), (e.DOMParser = i));
  },
  51: function (t, e) {
    e.entityMap = {
      lt: "<",
      gt: ">",
      amp: "&",
      quot: '"',
      apos: "'",
      Agrave: "À",
      Aacute: "Á",
      Acirc: "Â",
      Atilde: "Ã",
      Auml: "Ä",
      auml: "ä",
      Aring: "Å",
      aring: "å",
      AElig: "Æ",
      Ccedil: "Ç",
      Egrave: "È",
      Eacute: "É",
      Ecirc: "Ê",
      Euml: "Ë",
      Igrave: "Ì",
      Iacute: "Í",
      Icirc: "Î",
      Iuml: "Ï",
      ETH: "Ð",
      Ntilde: "Ñ",
      Ograve: "Ò",
      Oacute: "Ó",
      Ocirc: "Ô",
      Otilde: "Õ",
      Ouml: "Ö",
      ouml: "ö",
      Oslash: "Ø",
      Ugrave: "Ù",
      Uacute: "Ú",
      Ucirc: "Û",
      Uuml: "Ü",
      Yacute: "Ý",
      THORN: "Þ",
      szlig: "ß",
      agrave: "à",
      aacute: "á",
      acirc: "â",
      atilde: "ã",
      auml: "ä",
      aring: "å",
      aelig: "æ",
      ccedil: "ç",
      egrave: "è",
      eacute: "é",
      ecirc: "ê",
      euml: "ë",
      igrave: "ì",
      iacute: "í",
      icirc: "î",
      iuml: "ï",
      eth: "ð",
      ntilde: "ñ",
      ograve: "ò",
      oacute: "ó",
      ocirc: "ô",
      otilde: "õ",
      ouml: "ö",
      oslash: "ø",
      ugrave: "ù",
      uacute: "ú",
      ucirc: "û",
      uuml: "ü",
      yacute: "ý",
      thorn: "þ",
      yuml: "ÿ",
      nbsp: " ",
      iexcl: "¡",
      cent: "¢",
      pound: "£",
      curren: "¤",
      yen: "¥",
      brvbar: "¦",
      sect: "§",
      uml: "¨",
      copy: "©",
      ordf: "ª",
      laquo: "«",
      not: "¬",
      shy: "­­",
      reg: "®",
      macr: "¯",
      deg: "°",
      plusmn: "±",
      sup2: "²",
      sup3: "³",
      acute: "´",
      micro: "µ",
      para: "¶",
      middot: "·",
      cedil: "¸",
      sup1: "¹",
      ordm: "º",
      raquo: "»",
      frac14: "¼",
      frac12: "½",
      frac34: "¾",
      iquest: "¿",
      times: "×",
      divide: "÷",
      forall: "∀",
      part: "∂",
      exist: "∃",
      empty: "∅",
      nabla: "∇",
      isin: "∈",
      notin: "∉",
      ni: "∋",
      prod: "∏",
      sum: "∑",
      minus: "−",
      lowast: "∗",
      radic: "√",
      prop: "∝",
      infin: "∞",
      ang: "∠",
      and: "∧",
      or: "∨",
      cap: "∩",
      cup: "∪",
      int: "∫",
      there4: "∴",
      sim: "∼",
      cong: "≅",
      asymp: "≈",
      ne: "≠",
      equiv: "≡",
      le: "≤",
      ge: "≥",
      sub: "⊂",
      sup: "⊃",
      nsub: "⊄",
      sube: "⊆",
      supe: "⊇",
      oplus: "⊕",
      otimes: "⊗",
      perp: "⊥",
      sdot: "⋅",
      Alpha: "Α",
      Beta: "Β",
      Gamma: "Γ",
      Delta: "Δ",
      Epsilon: "Ε",
      Zeta: "Ζ",
      Eta: "Η",
      Theta: "Θ",
      Iota: "Ι",
      Kappa: "Κ",
      Lambda: "Λ",
      Mu: "Μ",
      Nu: "Ν",
      Xi: "Ξ",
      Omicron: "Ο",
      Pi: "Π",
      Rho: "Ρ",
      Sigma: "Σ",
      Tau: "Τ",
      Upsilon: "Υ",
      Phi: "Φ",
      Chi: "Χ",
      Psi: "Ψ",
      Omega: "Ω",
      alpha: "α",
      beta: "β",
      gamma: "γ",
      delta: "δ",
      epsilon: "ε",
      zeta: "ζ",
      eta: "η",
      theta: "θ",
      iota: "ι",
      kappa: "κ",
      lambda: "λ",
      mu: "μ",
      nu: "ν",
      xi: "ξ",
      omicron: "ο",
      pi: "π",
      rho: "ρ",
      sigmaf: "ς",
      sigma: "σ",
      tau: "τ",
      upsilon: "υ",
      phi: "φ",
      chi: "χ",
      psi: "ψ",
      omega: "ω",
      thetasym: "ϑ",
      upsih: "ϒ",
      piv: "ϖ",
      OElig: "Œ",
      oelig: "œ",
      Scaron: "Š",
      scaron: "š",
      Yuml: "Ÿ",
      fnof: "ƒ",
      circ: "ˆ",
      tilde: "˜",
      ensp: " ",
      emsp: " ",
      thinsp: " ",
      zwnj: "‌",
      zwj: "‍",
      lrm: "‎",
      rlm: "‏",
      ndash: "–",
      mdash: "—",
      lsquo: "‘",
      rsquo: "’",
      sbquo: "‚",
      ldquo: "“",
      rdquo: "”",
      bdquo: "„",
      dagger: "†",
      Dagger: "‡",
      bull: "•",
      hellip: "…",
      permil: "‰",
      prime: "′",
      Prime: "″",
      lsaquo: "‹",
      rsaquo: "›",
      oline: "‾",
      euro: "€",
      trade: "™",
      larr: "←",
      uarr: "↑",
      rarr: "→",
      darr: "↓",
      harr: "↔",
      crarr: "↵",
      lceil: "⌈",
      rceil: "⌉",
      lfloor: "⌊",
      rfloor: "⌋",
      loz: "◊",
      spades: "♠",
      clubs: "♣",
      hearts: "♥",
      diams: "♦",
    };
  },
  52: function (t, e) {
    var n =
        /[A-Z_a-z\xC0-\xD6\xD8-\xF6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD]/,
      i = new RegExp(
        "[\\-\\.0-9" +
          n.source.slice(1, -1) +
          "\\u00B7\\u0300-\\u036F\\u203F-\\u2040]",
      ),
      r = new RegExp(
        "^" + n.source + i.source + "*(?::" + n.source + i.source + "*)?$",
      );
    function s() {}
    function o(t, e) {
      return (
        (e.lineNumber = t.lineNumber),
        (e.columnNumber = t.columnNumber),
        e
      );
    }
    function a(t, e, n, i, r, s) {
      for (var o, a = ++e, h = 0; ; ) {
        var l = t.charAt(a);
        switch (l) {
          case "=":
            if (1 === h) ((o = t.slice(e, a)), (h = 3));
            else {
              if (2 !== h)
                throw new Error("attribute equal must after attrName");
              h = 3;
            }
            break;
          case "'":
          case '"':
            if (3 === h || 1 === h) {
              if (
                (1 === h &&
                  (s.warning('attribute value must after "="'),
                  (o = t.slice(e, a))),
                (e = a + 1),
                !((a = t.indexOf(l, e)) > 0))
              )
                throw new Error("attribute value no end '" + l + "' match");
              ((u = t.slice(e, a).replace(/&#?\w+;/g, r)),
                n.add(o, u, e - 1),
                (h = 5));
            } else {
              if (4 != h) throw new Error('attribute value must after "="');
              ((u = t.slice(e, a).replace(/&#?\w+;/g, r)),
                n.add(o, u, e),
                s.warning(
                  'attribute "' + o + '" missed start quot(' + l + ")!!",
                ),
                (e = a + 1),
                (h = 5));
            }
            break;
          case "/":
            switch (h) {
              case 0:
                n.setTagName(t.slice(e, a));
              case 5:
              case 6:
              case 7:
                ((h = 7), (n.closed = !0));
              case 4:
              case 1:
              case 2:
                break;
              default:
                throw new Error("attribute invalid close char('/')");
            }
            break;
          case "":
            return (
              s.error("unexpected end of input"),
              0 == h && n.setTagName(t.slice(e, a)),
              a
            );
          case ">":
            switch (h) {
              case 0:
                n.setTagName(t.slice(e, a));
              case 5:
              case 6:
              case 7:
                break;
              case 4:
              case 1:
                "/" === (u = t.slice(e, a)).slice(-1) &&
                  ((n.closed = !0), (u = u.slice(0, -1)));
              case 2:
                (2 === h && (u = o),
                  4 == h
                    ? (s.warning('attribute "' + u + '" missed quot(")!!'),
                      n.add(o, u.replace(/&#?\w+;/g, r), e))
                    : (("http://www.w3.org/1999/xhtml" === i[""] &&
                        u.match(/^(?:disabled|checked|selected)$/i)) ||
                        s.warning(
                          'attribute "' +
                            u +
                            '" missed value!! "' +
                            u +
                            '" instead!!',
                        ),
                      n.add(u, u, e)));
                break;
              case 3:
                throw new Error("attribute value missed!!");
            }
            return a;
          case "":
            l = " ";
          default:
            if (l <= " ")
              switch (h) {
                case 0:
                  (n.setTagName(t.slice(e, a)), (h = 6));
                  break;
                case 1:
                  ((o = t.slice(e, a)), (h = 2));
                  break;
                case 4:
                  var u = t.slice(e, a).replace(/&#?\w+;/g, r);
                  (s.warning('attribute "' + u + '" missed quot(")!!'),
                    n.add(o, u, e));
                case 5:
                  h = 6;
              }
            else
              switch (h) {
                case 2:
                  n.tagName;
                  (("http://www.w3.org/1999/xhtml" === i[""] &&
                    o.match(/^(?:disabled|checked|selected)$/i)) ||
                    s.warning(
                      'attribute "' +
                        o +
                        '" missed value!! "' +
                        o +
                        '" instead2!!',
                    ),
                    n.add(o, o, e),
                    (e = a),
                    (h = 1));
                  break;
                case 5:
                  s.warning('attribute space is required"' + o + '"!!');
                case 6:
                  ((h = 1), (e = a));
                  break;
                case 3:
                  ((h = 4), (e = a));
                  break;
                case 7:
                  throw new Error(
                    "elements closed character '/' and '>' must be connected to",
                  );
              }
        }
        a++;
      }
    }
    function h(t, e, n) {
      for (var i = t.tagName, r = null, s = t.length; s--; ) {
        var o = t[s],
          a = o.qName,
          h = o.value;
        if ((f = a.indexOf(":")) > 0)
          var l = (o.prefix = a.slice(0, f)),
            u = a.slice(f + 1),
            d = "xmlns" === l && u;
        else ((u = a), (l = null), (d = "xmlns" === a && ""));
        ((o.localName = u),
          !1 !== d &&
            (null == r && ((r = {}), c(n, (n = {}))),
            (n[d] = r[d] = h),
            (o.uri = "http://www.w3.org/2000/xmlns/"),
            e.startPrefixMapping(d, h)));
      }
      for (s = t.length; s--; ) {
        (l = (o = t[s]).prefix) &&
          ("xml" === l && (o.uri = "http://www.w3.org/XML/1998/namespace"),
          "xmlns" !== l && (o.uri = n[l || ""]));
      }
      var f;
      (f = i.indexOf(":")) > 0
        ? ((l = t.prefix = i.slice(0, f)), (u = t.localName = i.slice(f + 1)))
        : ((l = null), (u = t.localName = i));
      var p = (t.uri = n[l || ""]);
      if ((e.startElement(p, u, i, t), !t.closed))
        return ((t.currentNSMap = n), (t.localNSMap = r), !0);
      if ((e.endElement(p, u, i), r)) for (l in r) e.endPrefixMapping(l);
    }
    function l(t, e, n, i, r) {
      if (/^(?:script|textarea)$/i.test(n)) {
        var s = t.indexOf("</" + n + ">", e),
          o = t.substring(e + 1, s);
        if (/[&<]/.test(o))
          return /^script$/i.test(n)
            ? (r.characters(o, 0, o.length), s)
            : ((o = o.replace(/&#?\w+;/g, i)), r.characters(o, 0, o.length), s);
      }
      return e + 1;
    }
    function u(t, e, n, i) {
      var r = i[n];
      return (
        null == r &&
          ((r = t.lastIndexOf("</" + n + ">")) < e &&
            (r = t.lastIndexOf("</" + n)),
          (i[n] = r)),
        r < e
      );
    }
    function c(t, e) {
      for (var n in t) e[n] = t[n];
    }
    function d(t, e, n, i) {
      switch (t.charAt(e + 2)) {
        case "-":
          return "-" === t.charAt(e + 3)
            ? (r = t.indexOf("--\x3e", e + 4)) > e
              ? (n.comment(t, e + 4, r - e - 4), r + 3)
              : (i.error("Unclosed comment"), -1)
            : -1;
        default:
          if ("CDATA[" == t.substr(e + 3, 6)) {
            var r = t.indexOf("]]>", e + 9);
            return (
              n.startCDATA(),
              n.characters(t, e + 9, r - e - 9),
              n.endCDATA(),
              r + 3
            );
          }
          var s = (function (t, e) {
              var n,
                i = [],
                r = /'[^']+'|"[^"]+"|[^\s<>\/=]+=?|(\/?\s*>|<)/g;
              ((r.lastIndex = e), r.exec(t));
              for (; (n = r.exec(t)); ) if ((i.push(n), n[1])) return i;
            })(t, e),
            o = s.length;
          if (o > 1 && /!doctype/i.test(s[0][0])) {
            var a = s[1][0],
              h = o > 3 && /^public$/i.test(s[2][0]) && s[3][0],
              l = o > 4 && s[4][0],
              u = s[o - 1];
            return (
              n.startDTD(
                a,
                h && h.replace(/^(['"])(.*?)\1$/, "$2"),
                l && l.replace(/^(['"])(.*?)\1$/, "$2"),
              ),
              n.endDTD(),
              u.index + u[0].length
            );
          }
      }
      return -1;
    }
    function f(t, e, n) {
      var i = t.indexOf("?>", e);
      if (i) {
        var r = t.substring(e, i).match(/^<\?(\S*)\s*([\s\S]*?)\s*$/);
        if (r) {
          r[0].length;
          return (n.processingInstruction(r[1], r[2]), i + 2);
        }
        return -1;
      }
      return -1;
    }
    function p(t) {}
    ((s.prototype = {
      parse: function (t, e, n) {
        var i = this.domBuilder;
        (i.startDocument(),
          c(e, (e = {})),
          (function (t, e, n, i, r) {
            function s(t) {
              var e = t.slice(1, -1);
              return e in n
                ? n[e]
                : "#" === e.charAt(0)
                  ? (function (t) {
                      if (t > 65535) {
                        var e = 55296 + ((t -= 65536) >> 10),
                          n = 56320 + (1023 & t);
                        return String.fromCharCode(e, n);
                      }
                      return String.fromCharCode(t);
                    })(parseInt(e.substr(1).replace("x", "0x")))
                  : (r.error("entity not found:" + t), t);
            }
            function c(e) {
              if (e > _) {
                var n = t.substring(_, e).replace(/&#?\w+;/g, s);
                (b && g(_), i.characters(n, 0, e - _), (_ = e));
              }
            }
            function g(e, n) {
              for (; e >= v && (n = y.exec(t)); )
                ((m = n.index), (v = m + n[0].length), b.lineNumber++);
              b.columnNumber = e - m + 1;
            }
            var m = 0,
              v = 0,
              y = /.*(?:\r\n?|\n)|.*$/g,
              b = i.locator,
              w = [
                {
                  currentNSMap: e,
                },
              ],
              x = {},
              _ = 0;
            for (;;) {
              try {
                var E = t.indexOf("<", _);
                if (E < 0) {
                  if (!t.substr(_).match(/^\s*$/)) {
                    var k = i.doc,
                      S = k.createTextNode(t.substr(_));
                    (k.appendChild(S), (i.currentElement = S));
                  }
                  return;
                }
                switch ((E > _ && c(E), t.charAt(E + 1))) {
                  case "/":
                    var C = t.indexOf(">", E + 3),
                      T = t.substring(E + 2, C),
                      A = w.pop();
                    C < 0
                      ? ((T = t.substring(E + 2).replace(/[\s<].*/, "")),
                        r.error(
                          "end tag name: " +
                            T +
                            " is not complete:" +
                            A.tagName,
                        ),
                        (C = E + 1 + T.length))
                      : T.match(/\s</) &&
                        ((T = T.replace(/[\s<].*/, "")),
                        r.error("end tag name: " + T + " maybe not complete"),
                        (C = E + 1 + T.length));
                    var N = A.localNSMap,
                      O = A.tagName == T;
                    if (
                      O ||
                      (A.tagName && A.tagName.toLowerCase() == T.toLowerCase())
                    ) {
                      if ((i.endElement(A.uri, A.localName, T), N))
                        for (var I in N) i.endPrefixMapping(I);
                      O ||
                        r.fatalError(
                          "end tag name: " +
                            T +
                            " is not match the current start tagName:" +
                            A.tagName,
                        );
                    } else w.push(A);
                    C++;
                    break;
                  case "?":
                    (b && g(E), (C = f(t, E, i)));
                    break;
                  case "!":
                    (b && g(E), (C = d(t, E, i, r)));
                    break;
                  default:
                    b && g(E);
                    var R = new p(),
                      D = w[w.length - 1].currentNSMap,
                      L = ((C = a(t, E, R, D, s, r)), R.length);
                    if (
                      (!R.closed &&
                        u(t, C, R.tagName, x) &&
                        ((R.closed = !0),
                        n.nbsp || r.warning("unclosed xml attribute")),
                      b && L)
                    ) {
                      for (var j = o(b, {}), z = 0; z < L; z++) {
                        var P = R[z];
                        (g(P.offset), (P.locator = o(b, {})));
                      }
                      ((i.locator = j),
                        h(R, i, D) && w.push(R),
                        (i.locator = b));
                    } else h(R, i, D) && w.push(R);
                    "http://www.w3.org/1999/xhtml" !== R.uri || R.closed
                      ? C++
                      : (C = l(t, C, R.tagName, s, i));
                }
              } catch (t) {
                (r.error("element parse error: " + t), (C = -1));
              }
              C > _ ? (_ = C) : c(Math.max(E, _) + 1);
            }
          })(t, e, n, i, this.errorHandler),
          i.endDocument());
      },
    }),
      (p.prototype = {
        setTagName: function (t) {
          if (!r.test(t)) throw new Error("invalid tagName:" + t);
          this.tagName = t;
        },
        add: function (t, e, n) {
          if (!r.test(t)) throw new Error("invalid attribute:" + t);
          this[this.length++] = {
            qName: t,
            value: e,
            offset: n,
          };
        },
        length: 0,
        getLocalName: function (t) {
          return this[t].localName;
        },
        getLocator: function (t) {
          return this[t].locator;
        },
        getQName: function (t) {
          return this[t].qName;
        },
        getURI: function (t) {
          return this[t].uri;
        },
        getValue: function (t) {
          return this[t].value;
        },
      }),
      (e.XMLReader = s));
  },
};
