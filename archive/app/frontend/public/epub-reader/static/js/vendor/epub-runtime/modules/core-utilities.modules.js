/**
 * Auto-generated from the EPUB runtime source snapshot.
 * Responsibility: Core runtime helpers, URL/path handling, and shared primitives.
 * Module IDs: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9
 */
export const coreUtilityModules = {
  0: function (t, e, n) {
    "use strict";
    (n.r(e),
      n.d(e, "requestAnimationFrame", function () {
        return r;
      }),
      n.d(e, "uuid", function () {
        return o;
      }),
      n.d(e, "documentHeight", function () {
        return a;
      }),
      n.d(e, "isElement", function () {
        return h;
      }),
      n.d(e, "isNumber", function () {
        return l;
      }),
      n.d(e, "isFloat", function () {
        return u;
      }),
      n.d(e, "prefixed", function () {
        return c;
      }),
      n.d(e, "defaults", function () {
        return d;
      }),
      n.d(e, "extend", function () {
        return f;
      }),
      n.d(e, "insert", function () {
        return p;
      }),
      n.d(e, "locationOf", function () {
        return g;
      }),
      n.d(e, "indexOfSorted", function () {
        return m;
      }),
      n.d(e, "bounds", function () {
        return v;
      }),
      n.d(e, "borders", function () {
        return y;
      }),
      n.d(e, "nodeBounds", function () {
        return b;
      }),
      n.d(e, "windowBounds", function () {
        return w;
      }),
      n.d(e, "indexOfNode", function () {
        return x;
      }),
      n.d(e, "indexOfTextNode", function () {
        return _;
      }),
      n.d(e, "indexOfElementNode", function () {
        return E;
      }),
      n.d(e, "isXml", function () {
        return k;
      }),
      n.d(e, "createBlob", function () {
        return S;
      }),
      n.d(e, "createBlobUrl", function () {
        return C;
      }),
      n.d(e, "revokeBlobUrl", function () {
        return T;
      }),
      n.d(e, "createBase64Url", function () {
        return A;
      }),
      n.d(e, "type", function () {
        return N;
      }),
      n.d(e, "parse", function () {
        return O;
      }),
      n.d(e, "qs", function () {
        return I;
      }),
      n.d(e, "qsa", function () {
        return R;
      }),
      n.d(e, "qsp", function () {
        return D;
      }),
      n.d(e, "sprint", function () {
        return L;
      }),
      n.d(e, "treeWalker", function () {
        return j;
      }),
      n.d(e, "walk", function () {
        return z;
      }),
      n.d(e, "blob2base64", function () {
        return P;
      }),
      n.d(e, "defer", function () {
        return B;
      }),
      n.d(e, "querySelectorByType", function () {
        return M;
      }),
      n.d(e, "findChildren", function () {
        return F;
      }),
      n.d(e, "parents", function () {
        return U;
      }),
      n.d(e, "filterChildren", function () {
        return q;
      }),
      n.d(e, "getParentByTagName", function () {
        return W;
      }),
      n.d(e, "RangeObject", function () {
        return H;
      }));
    var i = n(18);
    const r =
        "undefined" != typeof window &&
        (window.requestAnimationFrame ||
          window.mozRequestAnimationFrame ||
          window.webkitRequestAnimationFrame ||
          window.msRequestAnimationFrame),
      s =
        "undefined" != typeof URL
          ? URL
          : "undefined" != typeof window
            ? window.URL || window.webkitURL || window.mozURL
            : void 0;
    function o() {
      var t = new Date().getTime();
      return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(
        /[xy]/g,
        function (e) {
          var n = ((t + 16 * Math.random()) % 16) | 0;
          return (
            (t = Math.floor(t / 16)),
            ("x" == e ? n : (7 & n) | 8).toString(16)
          );
        },
      );
    }
    function a() {
      return Math.max(
        document.documentElement.clientHeight,
        document.body.scrollHeight,
        document.documentElement.scrollHeight,
        document.body.offsetHeight,
        document.documentElement.offsetHeight,
      );
    }
    function h(t) {
      return !(!t || 1 != t.nodeType);
    }
    function l(t) {
      return !isNaN(parseFloat(t)) && isFinite(t);
    }
    function u(t) {
      let e = parseFloat(t);
      return (
        !1 !== l(t) &&
        (("string" == typeof t && t.indexOf(".") > -1) || Math.floor(e) !== e)
      );
    }
    function c(t) {
      var e = ["-webkit-", "-webkit-", "-moz-", "-o-", "-ms-"],
        n = t.toLowerCase(),
        i = ["Webkit", "webkit", "Moz", "O", "ms"].length;
      if ("undefined" == typeof document || void 0 !== document.body.style[n])
        return t;
      for (var r = 0; r < i; r++)
        if (void 0 !== document.body.style[e[r] + n]) return e[r] + n;
      return t;
    }
    function d(t) {
      for (var e = 1, n = arguments.length; e < n; e++) {
        var i = arguments[e];
        for (var r in i) void 0 === t[r] && (t[r] = i[r]);
      }
      return t;
    }
    function f(t) {
      var e = [].slice.call(arguments, 1);
      return (
        e.forEach(function (e) {
          e &&
            Object.getOwnPropertyNames(e).forEach(function (n) {
              Object.defineProperty(
                t,
                n,
                Object.getOwnPropertyDescriptor(e, n),
              );
            });
        }),
        t
      );
    }
    function p(t, e, n) {
      var i = g(t, e, n);
      return (e.splice(i, 0, t), i);
    }
    function g(t, e, n, i, r) {
      var s,
        o = i || 0,
        a = r || e.length,
        h = parseInt(o + (a - o) / 2);
      return (
        n ||
          (n = function (t, e) {
            return t > e ? 1 : t < e ? -1 : t == e ? 0 : void 0;
          }),
        a - o <= 0
          ? h
          : ((s = n(e[h], t)),
            a - o == 1
              ? s >= 0
                ? h
                : h + 1
              : 0 === s
                ? h
                : -1 === s
                  ? g(t, e, n, h, a)
                  : g(t, e, n, o, h))
      );
    }
    function m(t, e, n, i, r) {
      var s,
        o = i || 0,
        a = r || e.length,
        h = parseInt(o + (a - o) / 2);
      return (
        n ||
          (n = function (t, e) {
            return t > e ? 1 : t < e ? -1 : t == e ? 0 : void 0;
          }),
        a - o <= 0
          ? -1
          : ((s = n(e[h], t)),
            a - o == 1
              ? 0 === s
                ? h
                : -1
              : 0 === s
                ? h
                : -1 === s
                  ? m(t, e, n, h, a)
                  : m(t, e, n, o, h))
      );
    }
    function v(t) {
      var e = window.getComputedStyle(t),
        n = 0,
        i = 0;
      return (
        [
          "width",
          "paddingRight",
          "paddingLeft",
          "marginRight",
          "marginLeft",
          "borderRightWidth",
          "borderLeftWidth",
        ].forEach(function (t) {
          n += parseFloat(e[t]) || 0;
        }),
        [
          "height",
          "paddingTop",
          "paddingBottom",
          "marginTop",
          "marginBottom",
          "borderTopWidth",
          "borderBottomWidth",
        ].forEach(function (t) {
          i += parseFloat(e[t]) || 0;
        }),
        {
          height: i,
          width: n,
        }
      );
    }
    function y(t) {
      var e = window.getComputedStyle(t),
        n = 0,
        i = 0;
      return (
        [
          "paddingRight",
          "paddingLeft",
          "marginRight",
          "marginLeft",
          "borderRightWidth",
          "borderLeftWidth",
        ].forEach(function (t) {
          n += parseFloat(e[t]) || 0;
        }),
        [
          "paddingTop",
          "paddingBottom",
          "marginTop",
          "marginBottom",
          "borderTopWidth",
          "borderBottomWidth",
        ].forEach(function (t) {
          i += parseFloat(e[t]) || 0;
        }),
        {
          height: i,
          width: n,
        }
      );
    }
    function b(t) {
      let e,
        n = t.ownerDocument;
      if (t.nodeType == Node.TEXT_NODE) {
        let i = n.createRange();
        (i.selectNodeContents(t), (e = i.getBoundingClientRect()));
      } else e = t.getBoundingClientRect();
      return e;
    }
    function w() {
      var t = window.innerWidth,
        e = window.innerHeight;
      return {
        top: 0,
        left: 0,
        right: t,
        bottom: e,
        width: t,
        height: e,
      };
    }
    function x(t, e) {
      for (
        var n, i = t.parentNode.childNodes, r = -1, s = 0;
        s < i.length && ((n = i[s]).nodeType === e && r++, n != t);
        s++
      );
      return r;
    }
    function _(t) {
      return x(t, 3);
    }
    function E(t) {
      return x(t, 1);
    }
    function k(t) {
      return ["xml", "opf", "ncx"].indexOf(t) > -1;
    }
    function S(t, e) {
      return new Blob([t], {
        type: e,
      });
    }
    function C(t, e) {
      var n = S(t, e);
      return s.createObjectURL(n);
    }
    function T(t) {
      return s.revokeObjectURL(t);
    }
    function A(t, e) {
      if ("string" == typeof t)
        return "data:" + e + ";base64," + btoa(encodeURIComponent(t));
    }
    function N(t) {
      return Object.prototype.toString.call(t).slice(8, -1);
    }
    function O(t, e, n) {
      var r;
      return (
        (r = "undefined" == typeof DOMParser || n ? i.DOMParser : DOMParser),
        65279 === t.charCodeAt(0) && (t = t.slice(1)),
        new r().parseFromString(t, e)
      );
    }
    function I(t, e) {
      var n;
      if (!t) throw new Error("No Element Provided");
      return void 0 !== t.querySelector
        ? t.querySelector(e)
        : (n = t.getElementsByTagName(e)).length
          ? n[0]
          : void 0;
    }
    function R(t, e) {
      return void 0 !== t.querySelector
        ? t.querySelectorAll(e)
        : t.getElementsByTagName(e);
    }
    function D(t, e, n) {
      var i, r;
      if (void 0 !== t.querySelector) {
        for (var s in ((e += "["), n)) e += s + "~='" + n[s] + "'";
        return ((e += "]"), t.querySelector(e));
      }
      if (
        ((i = t.getElementsByTagName(e)),
        (r = Array.prototype.slice.call(i, 0).filter(function (t) {
          for (var e in n) if (t.getAttribute(e) === n[e]) return !0;
          return !1;
        })))
      )
        return r[0];
    }
    function L(t, e) {
      void 0 !== (t.ownerDocument || t).createTreeWalker
        ? j(t, e, NodeFilter.SHOW_TEXT)
        : z(t, function (t) {
            t && 3 === t.nodeType && e(t);
          });
    }
    function j(t, e, n) {
      var i = document.createTreeWalker(t, n, null, !1);
      let r;
      for (; (r = i.nextNode()); ) e(r);
    }
    function z(t, e) {
      if (e(t)) return !0;
      if ((t = t.firstChild))
        do {
          if (z(t, e)) return !0;
          t = t.nextSibling;
        } while (t);
    }
    function P(t) {
      return new Promise(function (e, n) {
        var i = new FileReader();
        (i.readAsDataURL(t),
          (i.onloadend = function () {
            e(i.result);
          }));
      });
    }
    function B() {
      ((this.resolve = null),
        (this.reject = null),
        (this.id = o()),
        (this.promise = new Promise((t, e) => {
          ((this.resolve = t), (this.reject = e));
        })),
        Object.freeze(this));
    }
    function M(t, e, n) {
      var i;
      if (
        (void 0 !== t.querySelector &&
          (i = t.querySelector(`${e}[*|type="${n}"]`)),
        i && 0 !== i.length)
      )
        return i;
      i = R(t, e);
      for (var r = 0; r < i.length; r++)
        if (
          i[r].getAttributeNS("http://www.idpf.org/2007/ops", "type") === n ||
          i[r].getAttribute("epub:type") === n
        )
          return i[r];
    }
    function F(t) {
      for (var e = [], n = t.childNodes, i = 0; i < n.length; i++) {
        let t = n[i];
        1 === t.nodeType && e.push(t);
      }
      return e;
    }
    function U(t) {
      for (var e = [t]; t; t = t.parentNode) e.unshift(t);
      return e;
    }
    function q(t, e, n) {
      for (var i = [], r = t.childNodes, s = 0; s < r.length; s++) {
        let t = r[s];
        if (1 === t.nodeType && t.nodeName.toLowerCase() === e) {
          if (n) return t;
          i.push(t);
        }
      }
      if (!n) return i;
    }
    function W(t, e) {
      let n;
      if (null !== t && "" !== e)
        for (n = t.parentNode; 1 === n.nodeType; ) {
          if (n.tagName.toLowerCase() === e) return n;
          n = n.parentNode;
        }
    }
    class H {
      constructor() {
        ((this.collapsed = !1),
          (this.commonAncestorContainer = void 0),
          (this.endContainer = void 0),
          (this.endOffset = void 0),
          (this.startContainer = void 0),
          (this.startOffset = void 0));
      }
      setStart(t, e) {
        ((this.startContainer = t),
          (this.startOffset = e),
          this.endContainer
            ? (this.commonAncestorContainer = this._commonAncestorContainer())
            : this.collapse(!0),
          this._checkCollapsed());
      }
      setEnd(t, e) {
        ((this.endContainer = t),
          (this.endOffset = e),
          this.startContainer
            ? ((this.collapsed = !1),
              (this.commonAncestorContainer = this._commonAncestorContainer()))
            : this.collapse(!1),
          this._checkCollapsed());
      }
      collapse(t) {
        ((this.collapsed = !0),
          t
            ? ((this.endContainer = this.startContainer),
              (this.endOffset = this.startOffset),
              (this.commonAncestorContainer = this.startContainer.parentNode))
            : ((this.startContainer = this.endContainer),
              (this.startOffset = this.endOffset),
              (this.commonAncestorContainer = this.endOffset.parentNode)));
      }
      selectNode(t) {
        let e = t.parentNode,
          n = Array.prototype.indexOf.call(e.childNodes, t);
        (this.setStart(e, n), this.setEnd(e, n + 1));
      }
      selectNodeContents(t) {
        t.childNodes[t.childNodes - 1];
        let e =
          3 === t.nodeType ? t.textContent.length : parent.childNodes.length;
        (this.setStart(t, 0), this.setEnd(t, e));
      }
      _commonAncestorContainer(t, e) {
        var n = U(t || this.startContainer),
          i = U(e || this.endContainer);
        if (n[0] == i[0])
          for (var r = 0; r < n.length; r++) if (n[r] != i[r]) return n[r - 1];
      }
      _checkCollapsed() {
        this.startContainer === this.endContainer &&
        this.startOffset === this.endOffset
          ? (this.collapsed = !0)
          : (this.collapsed = !1);
      }
      toString() {}
    }
  },
  1: function (t, e, n) {
    "use strict";
    (n.d(e, "b", function () {
      return i;
    }),
      n.d(e, "a", function () {
        return r;
      }),
      n.d(e, "c", function () {
        return s;
      }));
    const i = "0.3",
      r = [
        "keydown",
        "keyup",
        "keypressed",
        "mouseup",
        "mousedown",
        "click",
        "touchend",
        "touchstart",
        "touchmove",
      ],
      s = {
        BOOK: {
          OPEN_FAILED: "openFailed",
        },
        CONTENTS: {
          EXPAND: "expand",
          RESIZE: "resize",
          SELECTED: "selected",
          SELECTED_RANGE: "selectedRange",
          LINK_CLICKED: "linkClicked",
        },
        LOCATIONS: {
          CHANGED: "changed",
        },
        MANAGERS: {
          RESIZE: "resize",
          RESIZED: "resized",
          ORIENTATION_CHANGE: "orientationchange",
          ADDED: "added",
          SCROLL: "scroll",
          SCROLLED: "scrolled",
          REMOVED: "removed",
        },
        VIEWS: {
          AXIS: "axis",
          WRITING_MODE: "writingMode",
          LOAD_ERROR: "loaderror",
          RENDERED: "rendered",
          RESIZED: "resized",
          DISPLAYED: "displayed",
          SHOWN: "shown",
          HIDDEN: "hidden",
          MARK_CLICKED: "markClicked",
        },
        RENDITION: {
          STARTED: "started",
          ATTACHED: "attached",
          DISPLAYED: "displayed",
          DISPLAY_ERROR: "displayerror",
          RENDERED: "rendered",
          REMOVED: "removed",
          RESIZED: "resized",
          ORIENTATION_CHANGE: "orientationchange",
          LOCATION_CHANGED: "locationChanged",
          RELOCATED: "relocated",
          MARK_CLICKED: "markClicked",
          SELECTED: "selected",
          LAYOUT: "layout",
        },
        LAYOUT: {
          UPDATED: "updated",
        },
        ANNOTATION: {
          ATTACH: "attach",
          DETACH: "detach",
        },
      };
  },
  2: function (t, e, n) {
    "use strict";
    var i = n(0);
    class r {
      constructor(t, e, n) {
        var s;
        if (
          ((this.str = ""),
          (this.base = {}),
          (this.spinePos = 0),
          (this.range = !1),
          (this.path = {}),
          (this.start = null),
          (this.end = null),
          !(this instanceof r))
        )
          return new r(t, e, n);
        if (
          ("string" == typeof e
            ? (this.base = this.parseComponent(e))
            : "object" == typeof e && e.steps && (this.base = e),
          "string" === (s = this.checkType(t)))
        )
          return ((this.str = t), Object(i.extend)(this, this.parse(t)));
        if ("range" === s)
          return Object(i.extend)(this, this.fromRange(t, this.base, n));
        if ("node" === s)
          return Object(i.extend)(this, this.fromNode(t, this.base, n));
        if ("EpubCFI" === s && t.path) return t;
        if (t) throw new TypeError("not a valid argument for EpubCFI");
        return this;
      }
      checkType(t) {
        return this.isCfiString(t)
          ? "string"
          : !t ||
              "object" != typeof t ||
              ("Range" !== Object(i.type)(t) && void 0 === t.startContainer)
            ? t && "object" == typeof t && void 0 !== t.nodeType
              ? "node"
              : !!(t && "object" == typeof t && t instanceof r) && "EpubCFI"
            : "range";
      }
      parse(t) {
        var e,
          n,
          i,
          r = {
            spinePos: -1,
            range: !1,
            base: {},
            path: {},
            start: null,
            end: null,
          };
        return "string" != typeof t
          ? {
              spinePos: -1,
            }
          : (0 === t.indexOf("epubcfi(") &&
              ")" === t[t.length - 1] &&
              (t = t.slice(8, t.length - 1)),
            (e = this.getChapterComponent(t))
              ? ((r.base = this.parseComponent(e)),
                (n = this.getPathComponent(t)),
                (r.path = this.parseComponent(n)),
                (i = this.getRange(t)) &&
                  ((r.range = !0),
                  (r.start = this.parseComponent(i[0])),
                  (r.end = this.parseComponent(i[1]))),
                (r.spinePos = r.base.steps[1].index),
                r)
              : {
                  spinePos: -1,
                });
      }
      parseComponent(t) {
        var e,
          n = {
            steps: [],
            terminal: {
              offset: null,
              assertion: null,
            },
          },
          i = t.split(":"),
          r = i[0].split("/");
        return (
          i.length > 1 && ((e = i[1]), (n.terminal = this.parseTerminal(e))),
          "" === r[0] && r.shift(),
          (n.steps = r.map(
            function (t) {
              return this.parseStep(t);
            }.bind(this),
          )),
          n
        );
      }
      parseStep(t) {
        var e, n, i, r, s;
        if (
          ((r = t.match(/\[(.*)\]/)) && r[1] && (s = r[1]),
          (n = parseInt(t)),
          !isNaN(n))
        )
          return (
            n % 2 == 0
              ? ((e = "element"), (i = n / 2 - 1))
              : ((e = "text"), (i = (n - 1) / 2)),
            {
              type: e,
              index: i,
              id: s || null,
            }
          );
      }
      parseTerminal(t) {
        var e,
          n,
          r = t.match(/\[(.*)\]/);
        return (
          r && r[1]
            ? ((e = parseInt(t.split("[")[0])), (n = r[1]))
            : (e = parseInt(t)),
          Object(i.isNumber)(e) || (e = null),
          {
            offset: e,
            assertion: n,
          }
        );
      }
      getChapterComponent(t) {
        return t.split("!")[0];
      }
      getPathComponent(t) {
        var e = t.split("!");
        if (e[1]) {
          return e[1].split(",")[0];
        }
      }
      getRange(t) {
        var e = t.split(",");
        return 3 === e.length && [e[1], e[2]];
      }
      getCharecterOffsetComponent(t) {
        return t.split(":")[1] || "";
      }
      joinSteps(t) {
        return t
          ? t
              .map(function (t) {
                var e = "";
                return (
                  "element" === t.type && (e += 2 * (t.index + 1)),
                  "text" === t.type && (e += 1 + 2 * t.index),
                  t.id && (e += "[" + t.id + "]"),
                  e
                );
              })
              .join("/")
          : "";
      }
      segmentString(t) {
        var e = "/";
        return (
          (e += this.joinSteps(t.steps)),
          t.terminal &&
            null != t.terminal.offset &&
            (e += ":" + t.terminal.offset),
          t.terminal &&
            null != t.terminal.assertion &&
            (e += "[" + t.terminal.assertion + "]"),
          e
        );
      }
      toString() {
        var t = "epubcfi(";
        return (
          (t += this.segmentString(this.base)),
          (t += "!"),
          (t += this.segmentString(this.path)),
          this.range &&
            this.start &&
            ((t += ","), (t += this.segmentString(this.start))),
          this.range &&
            this.end &&
            ((t += ","), (t += this.segmentString(this.end))),
          (t += ")")
        );
      }
      compare(t, e) {
        var n, i, s, o;
        if (
          ("string" == typeof t && (t = new r(t)),
          "string" == typeof e && (e = new r(e)),
          t.spinePos > e.spinePos)
        )
          return 1;
        if (t.spinePos < e.spinePos) return -1;
        (t.range
          ? ((n = t.path.steps.concat(t.start.steps)), (s = t.start.terminal))
          : ((n = t.path.steps), (s = t.path.terminal)),
          e.range
            ? ((i = e.path.steps.concat(e.start.steps)), (o = e.start.terminal))
            : ((i = e.path.steps), (o = e.path.terminal)));
        for (var a = 0; a < n.length; a++) {
          if (!n[a]) return -1;
          if (!i[a]) return 1;
          if (n[a].index > i[a].index) return 1;
          if (n[a].index < i[a].index) return -1;
        }
        return n.length < i.length
          ? -1
          : s.offset > o.offset
            ? 1
            : s.offset < o.offset
              ? -1
              : 0;
      }
      step(t) {
        var e = 3 === t.nodeType ? "text" : "element";
        return {
          id: t.id,
          tagName: t.tagName,
          type: e,
          index: this.position(t),
        };
      }
      filteredStep(t, e) {
        var n,
          i = this.filter(t, e);
        if (i)
          return (
            (n = 3 === i.nodeType ? "text" : "element"),
            {
              id: i.id,
              tagName: i.tagName,
              type: n,
              index: this.filteredPosition(i, e),
            }
          );
      }
      pathTo(t, e, n) {
        for (
          var i,
            r = {
              steps: [],
              terminal: {
                offset: null,
                assertion: null,
              },
            },
            s = t;
          s && s.parentNode && 9 != s.parentNode.nodeType;
        )
          ((i = n ? this.filteredStep(s, n) : this.step(s)) &&
            r.steps.unshift(i),
            (s = s.parentNode));
        return (
          null != e &&
            e >= 0 &&
            ((r.terminal.offset = e),
            "text" != r.steps[r.steps.length - 1].type &&
              r.steps.push({
                type: "text",
                index: 0,
              })),
          r
        );
      }
      equalStep(t, e) {
        return (
          !(!t || !e) &&
          t.index === e.index &&
          t.id === e.id &&
          t.type === e.type
        );
      }
      fromRange(t, e, n) {
        var i = {
            range: !1,
            base: {},
            path: {},
            start: null,
            end: null,
          },
          r = t.startContainer,
          s = t.endContainer,
          o = t.startOffset,
          a = t.endOffset,
          h = !1;
        if (
          (n && (h = null != r.ownerDocument.querySelector("." + n)),
          "string" == typeof e
            ? ((i.base = this.parseComponent(e)),
              (i.spinePos = i.base.steps[1].index))
            : "object" == typeof e && (i.base = e),
          t.collapsed)
        )
          (h && (o = this.patchOffset(r, o, n)),
            (i.path = this.pathTo(r, o, n)));
        else {
          ((i.range = !0),
            h && (o = this.patchOffset(r, o, n)),
            (i.start = this.pathTo(r, o, n)),
            h && (a = this.patchOffset(s, a, n)),
            (i.end = this.pathTo(s, a, n)),
            (i.path = {
              steps: [],
              terminal: null,
            }));
          var l,
            u = i.start.steps.length;
          for (
            l = 0;
            l < u && this.equalStep(i.start.steps[l], i.end.steps[l]);
            l++
          )
            l === u - 1
              ? i.start.terminal === i.end.terminal &&
                (i.path.steps.push(i.start.steps[l]), (i.range = !1))
              : i.path.steps.push(i.start.steps[l]);
          ((i.start.steps = i.start.steps.slice(i.path.steps.length)),
            (i.end.steps = i.end.steps.slice(i.path.steps.length)));
        }
        return i;
      }
      fromNode(t, e, n) {
        var i = {
          range: !1,
          base: {},
          path: {},
          start: null,
          end: null,
        };
        return (
          "string" == typeof e
            ? ((i.base = this.parseComponent(e)),
              (i.spinePos = i.base.steps[1].index))
            : "object" == typeof e && (i.base = e),
          (i.path = this.pathTo(t, null, n)),
          i
        );
      }
      filter(t, e) {
        var n,
          i,
          r,
          s,
          o,
          a = !1;
        return (
          3 === t.nodeType
            ? ((a = !0),
              (r = t.parentNode),
              (n = t.parentNode.classList.contains(e)))
            : ((a = !1), (n = t.classList.contains(e))),
          n && a
            ? ((s = r.previousSibling),
              (o = r.nextSibling),
              s && 3 === s.nodeType
                ? (i = s)
                : o && 3 === o.nodeType && (i = o),
              i || t)
            : !(n && !a) && t
        );
      }
      patchOffset(t, e, n) {
        if (3 != t.nodeType) throw new Error("Anchor must be a text node");
        var i = t,
          r = e;
        for (
          t.parentNode.classList.contains(n) && (i = t.parentNode);
          i.previousSibling;
        ) {
          if (1 === i.previousSibling.nodeType) {
            if (!i.previousSibling.classList.contains(n)) break;
            r += i.previousSibling.textContent.length;
          } else r += i.previousSibling.textContent.length;
          i = i.previousSibling;
        }
        return r;
      }
      normalizedMap(t, e, n) {
        var i,
          r,
          s,
          o = {},
          a = -1,
          h = t.length;
        for (i = 0; i < h; i++)
          (1 === (r = t[i].nodeType) && t[i].classList.contains(n) && (r = 3),
            i > 0 && 3 === r && 3 === s
              ? (o[i] = a)
              : e === r && ((a += 1), (o[i] = a)),
            (s = r));
        return o;
      }
      position(t) {
        var e, n;
        return (
          1 === t.nodeType
            ? ((e = t.parentNode.children) ||
                (e = Object(i.findChildren)(t.parentNode)),
              (n = Array.prototype.indexOf.call(e, t)))
            : (n = (e = this.textNodes(t.parentNode)).indexOf(t)),
          n
        );
      }
      filteredPosition(t, e) {
        var n, i;
        return (
          1 === t.nodeType
            ? ((n = t.parentNode.children), (i = this.normalizedMap(n, 1, e)))
            : ((n = t.parentNode.childNodes),
              t.parentNode.classList.contains(e) &&
                (n = (t = t.parentNode).parentNode.childNodes),
              (i = this.normalizedMap(n, 3, e))),
          i[Array.prototype.indexOf.call(n, t)]
        );
      }
      stepsToXpath(t) {
        var e = [".", "*"];
        return (
          t.forEach(function (t) {
            var n = t.index + 1;
            t.id
              ? e.push("*[position()=" + n + " and @id='" + t.id + "']")
              : "text" === t.type
                ? e.push("text()[" + n + "]")
                : e.push("*[" + n + "]");
          }),
          e.join("/")
        );
      }
      stepsToQuerySelector(t) {
        var e = ["html"];
        return (
          t.forEach(function (t) {
            var n = t.index + 1;
            t.id
              ? e.push("#" + t.id)
              : "text" === t.type || e.push("*:nth-child(" + n + ")");
          }),
          e.join(">")
        );
      }
      textNodes(t, e) {
        return Array.prototype.slice.call(t.childNodes).filter(function (t) {
          return 3 === t.nodeType || !(!e || !t.classList.contains(e));
        });
      }
      walkToNode(t, e, n) {
        var r,
          s,
          o = e || document,
          a = o.documentElement,
          h = t.length;
        for (
          s = 0;
          s < h &&
          ("element" === (r = t[s]).type
            ? (a = r.id
                ? o.getElementById(r.id)
                : (a.children || Object(i.findChildren)(a))[r.index])
            : "text" === r.type && (a = this.textNodes(a, n)[r.index]),
          a);
          s++
        );
        return a;
      }
      findNode(t, e, n) {
        var i,
          r,
          s = e || document;
        return (
          n || void 0 === s.evaluate
            ? (i = n ? this.walkToNode(t, s, n) : this.walkToNode(t, s))
            : ((r = this.stepsToXpath(t)),
              (i = s.evaluate(
                r,
                s,
                null,
                XPathResult.FIRST_ORDERED_NODE_TYPE,
                null,
              ).singleNodeValue)),
          i
        );
      }
      fixMiss(t, e, n, i) {
        var r,
          s,
          o = this.findNode(t.slice(0, -1), n, i),
          a = o.childNodes,
          h = this.normalizedMap(a, 3, i),
          l = t[t.length - 1].index;
        for (let t in h) {
          if (!h.hasOwnProperty(t)) return;
          if (h[t] === l) {
            if (!(e > (s = (r = a[t]).textContent.length))) {
              o = 1 === r.nodeType ? r.childNodes[0] : r;
              break;
            }
            e -= s;
          }
        }
        return {
          container: o,
          offset: e,
        };
      }
      toRange(t, e) {
        var n,
          r,
          s,
          o,
          a,
          h,
          l,
          u,
          c = t || document,
          d = !!e && null != c.querySelector("." + e);
        if (
          ((n =
            void 0 !== c.createRange ? c.createRange() : new i.RangeObject()),
          this.range
            ? ((r = this.start),
              (h = this.path.steps.concat(r.steps)),
              (o = this.findNode(h, c, d ? e : null)),
              (s = this.end),
              (l = this.path.steps.concat(s.steps)),
              (a = this.findNode(l, c, d ? e : null)))
            : ((r = this.path),
              (h = this.path.steps),
              (o = this.findNode(this.path.steps, c, d ? e : null))),
          !o)
        )
          return (
            console.log("No startContainer found for", this.toString()),
            null
          );
        try {
          null != r.terminal.offset
            ? n.setStart(o, r.terminal.offset)
            : n.setStart(o, 0);
        } catch (t) {
          ((u = this.fixMiss(h, r.terminal.offset, c, d ? e : null)),
            n.setStart(u.container, u.offset));
        }
        if (a)
          try {
            null != s.terminal.offset
              ? n.setEnd(a, s.terminal.offset)
              : n.setEnd(a, 0);
          } catch (t) {
            ((u = this.fixMiss(l, this.end.terminal.offset, c, d ? e : null)),
              n.setEnd(u.container, u.offset));
          }
        return n;
      }
      isCfiString(t) {
        return (
          "string" == typeof t &&
          0 === t.indexOf("epubcfi(") &&
          ")" === t[t.length - 1]
        );
      }
      generateChapterComponent(t, e, n) {
        var i = "/" + 2 * (t + 1) + "/";
        return ((i += 2 * (parseInt(e) + 1)), n && (i += "[" + n + "]"), i);
      }
      collapse(t) {
        this.range &&
          ((this.range = !1),
          t
            ? ((this.path.steps = this.path.steps.concat(this.start.steps)),
              (this.path.terminal = this.start.terminal))
            : ((this.path.steps = this.path.steps.concat(this.end.steps)),
              (this.path.terminal = this.end.terminal)));
      }
    }
    e.a = r;
  },
  3: function (t, e, n) {
    "use strict";
    var i,
      r,
      s,
      o,
      a,
      h,
      l,
      u = n(33),
      c = n(50),
      d = Function.prototype.apply,
      f = Function.prototype.call,
      p = Object.create,
      g = Object.defineProperty,
      m = Object.defineProperties,
      v = Object.prototype.hasOwnProperty,
      y = {
        configurable: !0,
        enumerable: !1,
        writable: !0,
      };
    ((r = function (t, e) {
      var n, r;
      return (
        c(e),
        (r = this),
        i.call(
          this,
          t,
          (n = function () {
            (s.call(r, t, n), d.call(e, this, arguments));
          }),
        ),
        (n.__eeOnceListener__ = e),
        this
      );
    }),
      (a = {
        on: (i = function (t, e) {
          var n;
          return (
            c(e),
            v.call(this, "__ee__")
              ? (n = this.__ee__)
              : ((n = y.value = p(null)),
                g(this, "__ee__", y),
                (y.value = null)),
            n[t]
              ? "object" == typeof n[t]
                ? n[t].push(e)
                : (n[t] = [n[t], e])
              : (n[t] = e),
            this
          );
        }),
        once: r,
        off: (s = function (t, e) {
          var n, i, r, s;
          if ((c(e), !v.call(this, "__ee__"))) return this;
          if (!(n = this.__ee__)[t]) return this;
          if ("object" == typeof (i = n[t]))
            for (s = 0; (r = i[s]); ++s)
              (r !== e && r.__eeOnceListener__ !== e) ||
                (2 === i.length ? (n[t] = i[s ? 0 : 1]) : i.splice(s, 1));
          else (i !== e && i.__eeOnceListener__ !== e) || delete n[t];
          return this;
        }),
        emit: (o = function (t) {
          var e, n, i, r, s;
          if (v.call(this, "__ee__") && (r = this.__ee__[t]))
            if ("object" == typeof r) {
              for (
                n = arguments.length, s = new Array(n - 1), e = 1;
                e < n;
                ++e
              )
                s[e - 1] = arguments[e];
              for (r = r.slice(), e = 0; (i = r[e]); ++e) d.call(i, this, s);
            } else
              switch (arguments.length) {
                case 1:
                  f.call(r, this);
                  break;
                case 2:
                  f.call(r, this, arguments[1]);
                  break;
                case 3:
                  f.call(r, this, arguments[1], arguments[2]);
                  break;
                default:
                  for (
                    n = arguments.length, s = new Array(n - 1), e = 1;
                    e < n;
                    ++e
                  )
                    s[e - 1] = arguments[e];
                  d.call(r, this, s);
              }
        }),
      }),
      (h = {
        on: u(i),
        once: u(r),
        off: u(s),
        emit: u(o),
      }),
      (l = m({}, h)),
      (t.exports = e =
        function (t) {
          return null == t ? p(l) : m(Object(t), h);
        }),
      (e.methods = a));
  },
  4: function (t, e, n) {
    "use strict";
    var i = n(7),
      r = n.n(i);
    e.a = class {
      constructor(t) {
        var e;
        (t.indexOf("://") > -1 && (t = new URL(t).pathname),
          (e = this.parse(t)),
          (this.path = t),
          this.isDirectory(t)
            ? (this.directory = t)
            : (this.directory = e.dir + "/"),
          (this.filename = e.base),
          (this.extension = e.ext.slice(1)));
      }
      parse(t) {
        return r.a.parse(t);
      }
      isAbsolute(t) {
        return r.a.isAbsolute(t || this.path);
      }
      isDirectory(t) {
        return "/" === t.charAt(t.length - 1);
      }
      resolve(t) {
        return r.a.resolve(this.directory, t);
      }
      relative(t) {
        return t && t.indexOf("://") > -1 ? t : r.a.relative(this.directory, t);
      }
      splitPath(t) {
        return this.splitPathRe.exec(t).slice(1);
      }
      toString() {
        return this.path;
      }
    };
  },
  5: function (t, e, n) {
    "use strict";
    var i = n(4),
      r = n(7),
      s = n.n(r);
    e.a = class {
      constructor(t, e) {
        var n = t.indexOf("://") > -1,
          r = t;
        if (
          ((this.Url = void 0),
          (this.href = t),
          (this.protocol = ""),
          (this.origin = ""),
          (this.hash = ""),
          (this.hash = ""),
          (this.search = ""),
          (this.base = e),
          !n &&
            !1 !== e &&
            "string" != typeof e &&
            window &&
            window.location &&
            (this.base = window.location.href),
          n || this.base)
        )
          try {
            (this.base
              ? (this.Url = new URL(t, this.base))
              : (this.Url = new URL(t)),
              (this.href = this.Url.href),
              (this.protocol = this.Url.protocol),
              (this.origin = this.Url.origin),
              (this.hash = this.Url.hash),
              (this.search = this.Url.search),
              (r =
                this.Url.pathname + (this.Url.search ? this.Url.search : "")));
          } catch (t) {
            ((this.Url = void 0),
              this.base && (r = new i.a(this.base).resolve(r)));
          }
        ((this.Path = new i.a(r)),
          (this.directory = this.Path.directory),
          (this.filename = this.Path.filename),
          (this.extension = this.Path.extension));
      }
      path() {
        return this.Path;
      }
      resolve(t) {
        var e;
        return t.indexOf("://") > -1
          ? t
          : ((e = s.a.resolve(this.directory, t)), this.origin + e);
      }
      relative(t) {
        return s.a.relative(t, this.directory);
      }
      toString() {
        return this.href;
      }
    };
  },
  6: function (t, e, n) {
    "use strict";
    e.a = class {
      constructor(t) {
        ((this.context = t || this), (this.hooks = []));
      }
      register() {
        for (var t = 0; t < arguments.length; ++t)
          if ("function" == typeof arguments[t]) this.hooks.push(arguments[t]);
          else
            for (var e = 0; e < arguments[t].length; ++e)
              this.hooks.push(arguments[t][e]);
      }
      deregister(t) {
        let e;
        for (let n = 0; n < this.hooks.length; n++)
          if (((e = this.hooks[n]), e === t)) {
            this.hooks.splice(n, 1);
            break;
          }
      }
      trigger() {
        var t = arguments,
          e = this.context,
          n = [];
        return (
          this.hooks.forEach(function (i) {
            var r = i.apply(e, t);
            r && "function" == typeof r.then && n.push(r);
          }),
          Promise.all(n)
        );
      }
      list() {
        return this.hooks;
      }
      clear() {
        return (this.hooks = []);
      }
    };
  },
  7: function (t, e, n) {
    "use strict";
    if (!i)
      var i = {
        cwd: function () {
          return "/";
        },
      };
    function r(t) {
      if ("string" != typeof t)
        throw new TypeError("Path must be a string. Received " + t);
    }
    function s(t, e) {
      for (var n, i = "", r = -1, s = 0, o = 0; o <= t.length; ++o) {
        if (o < t.length) n = t.charCodeAt(o);
        else {
          if (47 === n) break;
          n = 47;
        }
        if (47 === n) {
          if (r === o - 1 || 1 === s);
          else if (r !== o - 1 && 2 === s) {
            if (
              i.length < 2 ||
              46 !== i.charCodeAt(i.length - 1) ||
              46 !== i.charCodeAt(i.length - 2)
            )
              if (i.length > 2) {
                for (
                  var a = i.length - 1, h = a;
                  h >= 0 && 47 !== i.charCodeAt(h);
                  --h
                );
                if (h !== a) {
                  ((i = -1 === h ? "" : i.slice(0, h)), (r = o), (s = 0));
                  continue;
                }
              } else if (2 === i.length || 1 === i.length) {
                ((i = ""), (r = o), (s = 0));
                continue;
              }
            e && (i.length > 0 ? (i += "/..") : (i = ".."));
          } else
            i.length > 0
              ? (i += "/" + t.slice(r + 1, o))
              : (i = t.slice(r + 1, o));
          ((r = o), (s = 0));
        } else 46 === n && -1 !== s ? ++s : (s = -1);
      }
      return i;
    }
    var o = {
      resolve: function () {
        for (
          var t, e = "", n = !1, o = arguments.length - 1;
          o >= -1 && !n;
          o--
        ) {
          var a;
          (o >= 0
            ? (a = arguments[o])
            : (void 0 === t && (t = i.cwd()), (a = t)),
            r(a),
            0 !== a.length &&
              ((e = a + "/" + e), (n = 47 === a.charCodeAt(0))));
        }
        return (
          (e = s(e, !n)),
          n ? (e.length > 0 ? "/" + e : "/") : e.length > 0 ? e : "."
        );
      },
      normalize: function (t) {
        if ((r(t), 0 === t.length)) return ".";
        var e = 47 === t.charCodeAt(0),
          n = 47 === t.charCodeAt(t.length - 1);
        return (
          0 !== (t = s(t, !e)).length || e || (t = "."),
          t.length > 0 && n && (t += "/"),
          e ? "/" + t : t
        );
      },
      isAbsolute: function (t) {
        return (r(t), t.length > 0 && 47 === t.charCodeAt(0));
      },
      join: function () {
        if (0 === arguments.length) return ".";
        for (var t, e = 0; e < arguments.length; ++e) {
          var n = arguments[e];
          (r(n), n.length > 0 && (void 0 === t ? (t = n) : (t += "/" + n)));
        }
        return void 0 === t ? "." : o.normalize(t);
      },
      relative: function (t, e) {
        if ((r(t), r(e), t === e)) return "";
        if ((t = o.resolve(t)) === (e = o.resolve(e))) return "";
        for (var n = 1; n < t.length && 47 === t.charCodeAt(n); ++n);
        for (
          var i = t.length, s = i - n, a = 1;
          a < e.length && 47 === e.charCodeAt(a);
          ++a
        );
        for (
          var h = e.length - a, l = s < h ? s : h, u = -1, c = 0;
          c <= l;
          ++c
        ) {
          if (c === l) {
            if (h > l) {
              if (47 === e.charCodeAt(a + c)) return e.slice(a + c + 1);
              if (0 === c) return e.slice(a + c);
            } else
              s > l &&
                (47 === t.charCodeAt(n + c) ? (u = c) : 0 === c && (u = 0));
            break;
          }
          var d = t.charCodeAt(n + c);
          if (d !== e.charCodeAt(a + c)) break;
          47 === d && (u = c);
        }
        var f = "";
        for (c = n + u + 1; c <= i; ++c)
          (c !== i && 47 !== t.charCodeAt(c)) ||
            (0 === f.length ? (f += "..") : (f += "/.."));
        return f.length > 0
          ? f + e.slice(a + u)
          : ((a += u), 47 === e.charCodeAt(a) && ++a, e.slice(a));
      },
      _makeLong: function (t) {
        return t;
      },
      dirname: function (t) {
        if ((r(t), 0 === t.length)) return ".";
        for (
          var e = t.charCodeAt(0),
            n = 47 === e,
            i = -1,
            s = !0,
            o = t.length - 1;
          o >= 1;
          --o
        )
          if (47 === (e = t.charCodeAt(o))) {
            if (!s) {
              i = o;
              break;
            }
          } else s = !1;
        return -1 === i ? (n ? "/" : ".") : n && 1 === i ? "//" : t.slice(0, i);
      },
      basename: function (t, e) {
        if (void 0 !== e && "string" != typeof e)
          throw new TypeError('"ext" argument must be a string');
        r(t);
        var n,
          i = 0,
          s = -1,
          o = !0;
        if (void 0 !== e && e.length > 0 && e.length <= t.length) {
          if (e.length === t.length && e === t) return "";
          var a = e.length - 1,
            h = -1;
          for (n = t.length - 1; n >= 0; --n) {
            var l = t.charCodeAt(n);
            if (47 === l) {
              if (!o) {
                i = n + 1;
                break;
              }
            } else
              (-1 === h && ((o = !1), (h = n + 1)),
                a >= 0 &&
                  (l === e.charCodeAt(a)
                    ? -1 == --a && (s = n)
                    : ((a = -1), (s = h))));
          }
          return (
            i === s ? (s = h) : -1 === s && (s = t.length),
            t.slice(i, s)
          );
        }
        for (n = t.length - 1; n >= 0; --n)
          if (47 === t.charCodeAt(n)) {
            if (!o) {
              i = n + 1;
              break;
            }
          } else -1 === s && ((o = !1), (s = n + 1));
        return -1 === s ? "" : t.slice(i, s);
      },
      extname: function (t) {
        r(t);
        for (
          var e = -1, n = 0, i = -1, s = !0, o = 0, a = t.length - 1;
          a >= 0;
          --a
        ) {
          var h = t.charCodeAt(a);
          if (47 !== h)
            (-1 === i && ((s = !1), (i = a + 1)),
              46 === h
                ? -1 === e
                  ? (e = a)
                  : 1 !== o && (o = 1)
                : -1 !== e && (o = -1));
          else if (!s) {
            n = a + 1;
            break;
          }
        }
        return -1 === e ||
          -1 === i ||
          0 === o ||
          (1 === o && e === i - 1 && e === n + 1)
          ? ""
          : t.slice(e, i);
      },
      format: function (t) {
        if (null === t || "object" != typeof t)
          throw new TypeError(
            'Parameter "pathObject" must be an object, not ' + typeof t,
          );
        return (function (t, e) {
          var n = e.dir || e.root,
            i = e.base || (e.name || "") + (e.ext || "");
          return n ? (n === e.root ? n + i : n + t + i) : i;
        })("/", t);
      },
      parse: function (t) {
        r(t);
        var e = {
          root: "",
          dir: "",
          base: "",
          ext: "",
          name: "",
        };
        if (0 === t.length) return e;
        var n,
          i = t.charCodeAt(0),
          s = 47 === i;
        s ? ((e.root = "/"), (n = 1)) : (n = 0);
        for (
          var o = -1, a = 0, h = -1, l = !0, u = t.length - 1, c = 0;
          u >= n;
          --u
        )
          if (47 !== (i = t.charCodeAt(u)))
            (-1 === h && ((l = !1), (h = u + 1)),
              46 === i
                ? -1 === o
                  ? (o = u)
                  : 1 !== c && (c = 1)
                : -1 !== o && (c = -1));
          else if (!l) {
            a = u + 1;
            break;
          }
        return (
          -1 === o ||
          -1 === h ||
          0 === c ||
          (1 === c && o === h - 1 && o === a + 1)
            ? -1 !== h &&
              (e.base = e.name = 0 === a && s ? t.slice(1, h) : t.slice(a, h))
            : (0 === a && s
                ? ((e.name = t.slice(1, o)), (e.base = t.slice(1, h)))
                : ((e.name = t.slice(a, o)), (e.base = t.slice(a, h))),
              (e.ext = t.slice(o, h))),
          a > 0 ? (e.dir = t.slice(0, a - 1)) : s && (e.dir = "/"),
          e
        );
      },
      sep: "/",
      delimiter: ":",
      posix: null,
    };
    t.exports = o;
  },
  8: function (t, e, n) {
    "use strict";
    (n.d(e, "a", function () {
      return s;
    }),
      n.d(e, "b", function () {
        return o;
      }),
      n.d(e, "d", function () {
        return a;
      }),
      n.d(e, "c", function () {
        return h;
      }),
      n.d(e, "e", function () {
        return l;
      }));
    var i = n(0),
      r = n(5);
    n(4);
    function s(t, e) {
      var n,
        r,
        s = e.url,
        o = s.indexOf("://") > -1;
      t &&
        ((r = Object(i.qs)(t, "head")),
        (n = Object(i.qs)(r, "base")) ||
          ((n = t.createElement("base")), r.insertBefore(n, r.firstChild)),
        !o && window && window.location && (s = window.location.origin + s),
        n.setAttribute("href", s));
    }
    function o(t, e) {
      var n,
        r,
        s = e.canonical;
      t &&
        ((n = Object(i.qs)(t, "head")),
        (r = Object(i.qs)(n, "link[rel='canonical']"))
          ? r.setAttribute("href", s)
          : ((r = t.createElement("link")).setAttribute("rel", "canonical"),
            r.setAttribute("href", s),
            n.appendChild(r)));
    }
    function a(t, e) {
      var n,
        r,
        s = e.idref;
      t &&
        ((n = Object(i.qs)(t, "head")),
        (r = Object(i.qs)(n, "link[property='dc.identifier']"))
          ? r.setAttribute("content", s)
          : ((r = t.createElement("meta")).setAttribute(
              "name",
              "dc.identifier",
            ),
            r.setAttribute("content", s),
            n.appendChild(r)));
    }
    function h(t, e) {
      var n = t.querySelectorAll("a[href]");
      if (n.length)
        for (
          var s = Object(i.qs)(t.ownerDocument, "base"),
            o = s ? s.getAttribute("href") : void 0,
            a = function (t) {
              var n = t.getAttribute("href");
              if (0 !== n.indexOf("mailto:"))
                if (n.indexOf("://") > -1) t.setAttribute("target", "_blank");
                else {
                  var i;
                  try {
                    i = new r.a(n, o);
                  } catch (t) {}
                  t.onclick = function () {
                    return (
                      i && i.hash
                        ? e(i.Path.path + i.hash)
                        : e(i ? i.Path.path : n),
                      !1
                    );
                  };
                }
            }.bind(this),
            h = 0;
          h < n.length;
          h++
        )
          a(n[h]);
    }
    function l(t, e, n) {
      return (
        e.forEach(function (e, i) {
          e &&
            n[i] &&
            ((e = e.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, "\\$&")),
            (t = t.replace(new RegExp(e, "g"), n[i])));
        }),
        t
      );
    }
  },
  9: function (t, e) {
    var n;
    n = (function () {
      return this;
    })();
    try {
      n = n || new Function("return this")();
    } catch (t) {
      "object" == typeof window && (n = window);
    }
    t.exports = n;
  },
};
