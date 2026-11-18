/**
 * Auto-generated from the EPUB runtime source snapshot.
 * Responsibility: Object/type/string polyfills and numeric coercion helpers.
 * Module IDs: 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 55, 56, 57, 58, 59, 60, 61, 62
 */
export const compatibilityShimModules = {
  33: function (t, e, n) {
    "use strict";
    var i = n(25),
      r = n(34),
      s = n(38),
      o = n(46),
      a = n(47);
    (t.exports = function (t, e) {
      var n, r, h, l, u;
      return (
        arguments.length < 2 || "string" != typeof t
          ? ((l = e), (e = t), (t = null))
          : (l = arguments[2]),
        i(t)
          ? ((n = a.call(t, "c")), (r = a.call(t, "e")), (h = a.call(t, "w")))
          : ((n = h = !0), (r = !1)),
        (u = {
          value: e,
          configurable: n,
          enumerable: r,
          writable: h,
        }),
        l ? s(o(l), u) : u
      );
    }).gs = function (t, e, n) {
      var h, l, u, c;
      return (
        "string" != typeof t
          ? ((u = n), (n = e), (e = t), (t = null))
          : (u = arguments[3]),
        i(e)
          ? r(e)
            ? i(n)
              ? r(n) || ((u = n), (n = void 0))
              : (n = void 0)
            : ((u = e), (e = n = void 0))
          : (e = void 0),
        i(t)
          ? ((h = a.call(t, "c")), (l = a.call(t, "e")))
          : ((h = !0), (l = !1)),
        (c = {
          get: e,
          set: n,
          configurable: h,
          enumerable: l,
        }),
        u ? s(o(u), c) : c
      );
    };
  },
  34: function (t, e, n) {
    "use strict";
    var i = n(35),
      r = /^\s*class[\s{/}]/,
      s = Function.prototype.toString;
    t.exports = function (t) {
      return !!i(t) && !r.test(s.call(t));
    };
  },
  35: function (t, e, n) {
    "use strict";
    var i = n(36);
    t.exports = function (t) {
      if ("function" != typeof t) return !1;
      if (!hasOwnProperty.call(t, "length")) return !1;
      try {
        if ("number" != typeof t.length) return !1;
        if ("function" != typeof t.call) return !1;
        if ("function" != typeof t.apply) return !1;
      } catch (t) {
        return !1;
      }
      return !i(t);
    };
  },
  36: function (t, e, n) {
    "use strict";
    var i = n(37);
    t.exports = function (t) {
      if (!i(t)) return !1;
      try {
        return !!t.constructor && t.constructor.prototype === t;
      } catch (t) {
        return !1;
      }
    };
  },
  37: function (t, e, n) {
    "use strict";
    var i = n(25),
      r = {
        object: !0,
        function: !0,
        undefined: !0,
      };
    t.exports = function (t) {
      return !!i(t) && hasOwnProperty.call(r, typeof t);
    };
  },
  38: function (t, e, n) {
    "use strict";
    t.exports = n(39)() ? Object.assign : n(40);
  },
  39: function (t, e, n) {
    "use strict";
    t.exports = function () {
      var t,
        e = Object.assign;
      return (
        "function" == typeof e &&
        (e(
          (t = {
            foo: "raz",
          }),
          {
            bar: "dwa",
          },
          {
            trzy: "trzy",
          },
        ),
        t.foo + t.bar + t.trzy === "razdwatrzy")
      );
    };
  },
  40: function (t, e, n) {
    "use strict";
    var i = n(41),
      r = n(45),
      s = Math.max;
    t.exports = function (t, e) {
      var n,
        o,
        a,
        h = s(arguments.length, 2);
      for (
        t = Object(r(t)),
          a = function (i) {
            try {
              t[i] = e[i];
            } catch (t) {
              n || (n = t);
            }
          },
          o = 1;
        o < h;
        ++o
      )
        i((e = arguments[o])).forEach(a);
      if (void 0 !== n) throw n;
      return t;
    };
  },
  41: function (t, e, n) {
    "use strict";
    t.exports = n(42)() ? Object.keys : n(43);
  },
  42: function (t, e, n) {
    "use strict";
    t.exports = function () {
      try {
        return (Object.keys("primitive"), !0);
      } catch (t) {
        return !1;
      }
    };
  },
  43: function (t, e, n) {
    "use strict";
    var i = n(19),
      r = Object.keys;
    t.exports = function (t) {
      return r(i(t) ? Object(t) : t);
    };
  },
  44: function (t, e, n) {
    "use strict";
    t.exports = function () {};
  },
  45: function (t, e, n) {
    "use strict";
    var i = n(19);
    t.exports = function (t) {
      if (!i(t)) throw new TypeError("Cannot use null or undefined");
      return t;
    };
  },
  46: function (t, e, n) {
    "use strict";
    var i = n(19),
      r = Array.prototype.forEach,
      s = Object.create,
      o = function (t, e) {
        var n;
        for (n in t) e[n] = t[n];
      };
    t.exports = function (t) {
      var e = s(null);
      return (
        r.call(arguments, function (t) {
          i(t) && o(Object(t), e);
        }),
        e
      );
    };
  },
  47: function (t, e, n) {
    "use strict";
    t.exports = n(48)() ? String.prototype.contains : n(49);
  },
  48: function (t, e, n) {
    "use strict";
    var i = "razdwatrzy";
    t.exports = function () {
      return (
        "function" == typeof i.contains &&
        !0 === i.contains("dwa") &&
        !1 === i.contains("foo")
      );
    };
  },
  49: function (t, e, n) {
    "use strict";
    var i = String.prototype.indexOf;
    t.exports = function (t) {
      return i.call(this, t, arguments[1]) > -1;
    };
  },
  50: function (t, e, n) {
    "use strict";
    t.exports = function (t) {
      if ("function" != typeof t) throw new TypeError(t + " is not a function");
      return t;
    };
  },
  55: function (t, e, n) {
    var i = n(27);
    t.exports = function () {
      return i.Date.now();
    };
  },
  56: function (t, e, n) {
    (function (e) {
      var n = "object" == typeof e && e && e.Object === Object && e;
      t.exports = n;
    }).call(this, n(9));
  },
  57: function (t, e, n) {
    var i = n(20),
      r = n(58),
      s = /^\s+|\s+$/g,
      o = /^[-+]0x[0-9a-f]+$/i,
      a = /^0b[01]+$/i,
      h = /^0o[0-7]+$/i,
      l = parseInt;
    t.exports = function (t) {
      if ("number" == typeof t) return t;
      if (r(t)) return NaN;
      if (i(t)) {
        var e = "function" == typeof t.valueOf ? t.valueOf() : t;
        t = i(e) ? e + "" : e;
      }
      if ("string" != typeof t) return 0 === t ? t : +t;
      t = t.replace(s, "");
      var n = a.test(t);
      return n || h.test(t) ? l(t.slice(2), n ? 2 : 8) : o.test(t) ? NaN : +t;
    };
  },
  58: function (t, e, n) {
    var i = n(59),
      r = n(62);
    t.exports = function (t) {
      return "symbol" == typeof t || (r(t) && "[object Symbol]" == i(t));
    };
  },
  59: function (t, e, n) {
    var i = n(28),
      r = n(60),
      s = n(61),
      o = i ? i.toStringTag : void 0;
    t.exports = function (t) {
      return null == t
        ? void 0 === t
          ? "[object Undefined]"
          : "[object Null]"
        : o && o in Object(t)
          ? r(t)
          : s(t);
    };
  },
  60: function (t, e, n) {
    var i = n(28),
      r = Object.prototype,
      s = r.hasOwnProperty,
      o = r.toString,
      a = i ? i.toStringTag : void 0;
    t.exports = function (t) {
      var e = s.call(t, a),
        n = t[a];
      try {
        t[a] = void 0;
        var i = !0;
      } catch (t) {}
      var r = o.call(t);
      return (i && (e ? (t[a] = n) : delete t[a]), r);
    };
  },
  61: function (t, e) {
    var n = Object.prototype.toString;
    t.exports = function (t) {
      return n.call(t);
    };
  },
  62: function (t, e) {
    t.exports = function (t) {
      return null != t && "object" == typeof t;
    };
  },
};
