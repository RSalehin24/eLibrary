/**
 * Auto-generated from the EPUB runtime source snapshot.
 * Responsibility: setImmediate/process-like scheduling shims for browser runtime.
 * Module IDs: 67, 68, 69
 */
export const asyncSchedulingModules = {
  67: function (t, e, n) {
    (function (t) {
      var i =
          (void 0 !== t && t) || ("undefined" != typeof self && self) || window,
        r = Function.prototype.apply;
      function s(t, e) {
        ((this._id = t), (this._clearFn = e));
      }
      ((e.setTimeout = function () {
        return new s(r.call(setTimeout, i, arguments), clearTimeout);
      }),
        (e.setInterval = function () {
          return new s(r.call(setInterval, i, arguments), clearInterval);
        }),
        (e.clearTimeout = e.clearInterval =
          function (t) {
            t && t.close();
          }),
        (s.prototype.unref = s.prototype.ref = function () {}),
        (s.prototype.close = function () {
          this._clearFn.call(i, this._id);
        }),
        (e.enroll = function (t, e) {
          (clearTimeout(t._idleTimeoutId), (t._idleTimeout = e));
        }),
        (e.unenroll = function (t) {
          (clearTimeout(t._idleTimeoutId), (t._idleTimeout = -1));
        }),
        (e._unrefActive = e.active =
          function (t) {
            clearTimeout(t._idleTimeoutId);
            var e = t._idleTimeout;
            e >= 0 &&
              (t._idleTimeoutId = setTimeout(function () {
                t._onTimeout && t._onTimeout();
              }, e));
          }),
        n(68),
        (e.setImmediate =
          ("undefined" != typeof self && self.setImmediate) ||
          (void 0 !== t && t.setImmediate) ||
          (this && this.setImmediate)),
        (e.clearImmediate =
          ("undefined" != typeof self && self.clearImmediate) ||
          (void 0 !== t && t.clearImmediate) ||
          (this && this.clearImmediate)));
    }).call(this, n(9));
  },
  68: function (t, e, n) {
    (function (t, e) {
      !(function (t, n) {
        "use strict";
        if (!t.setImmediate) {
          var i,
            r,
            s,
            o,
            a,
            h = 1,
            l = {},
            u = !1,
            c = t.document,
            d = Object.getPrototypeOf && Object.getPrototypeOf(t);
          ((d = d && d.setTimeout ? d : t),
            "[object process]" === {}.toString.call(t.process)
              ? (i = function (t) {
                  e.nextTick(function () {
                    p(t);
                  });
                })
              : !(function () {
                    if (t.postMessage && !t.importScripts) {
                      var e = !0,
                        n = t.onmessage;
                      return (
                        (t.onmessage = function () {
                          e = !1;
                        }),
                        t.postMessage("", "*"),
                        (t.onmessage = n),
                        e
                      );
                    }
                  })()
                ? t.MessageChannel
                  ? (((s = new MessageChannel()).port1.onmessage = function (
                      t,
                    ) {
                      p(t.data);
                    }),
                    (i = function (t) {
                      s.port2.postMessage(t);
                    }))
                  : c && "onreadystatechange" in c.createElement("script")
                    ? ((r = c.documentElement),
                      (i = function (t) {
                        var e = c.createElement("script");
                        ((e.onreadystatechange = function () {
                          (p(t),
                            (e.onreadystatechange = null),
                            r.removeChild(e),
                            (e = null));
                        }),
                          r.appendChild(e));
                      }))
                    : (i = function (t) {
                        setTimeout(p, 0, t);
                      })
                : ((o = "setImmediate$" + Math.random() + "$"),
                  (a = function (e) {
                    e.source === t &&
                      "string" == typeof e.data &&
                      0 === e.data.indexOf(o) &&
                      p(+e.data.slice(o.length));
                  }),
                  t.addEventListener
                    ? t.addEventListener("message", a, !1)
                    : t.attachEvent("onmessage", a),
                  (i = function (e) {
                    t.postMessage(o + e, "*");
                  })),
            (d.setImmediate = function (t) {
              "function" != typeof t && (t = new Function("" + t));
              for (
                var e = new Array(arguments.length - 1), n = 0;
                n < e.length;
                n++
              )
                e[n] = arguments[n + 1];
              var r = {
                callback: t,
                args: e,
              };
              return ((l[h] = r), i(h), h++);
            }),
            (d.clearImmediate = f));
        }
        function f(t) {
          delete l[t];
        }
        function p(t) {
          if (u) setTimeout(p, 0, t);
          else {
            var e = l[t];
            if (e) {
              u = !0;
              try {
                !(function (t) {
                  var e = t.callback,
                    n = t.args;
                  switch (n.length) {
                    case 0:
                      e();
                      break;
                    case 1:
                      e(n[0]);
                      break;
                    case 2:
                      e(n[0], n[1]);
                      break;
                    case 3:
                      e(n[0], n[1], n[2]);
                      break;
                    default:
                      e.apply(void 0, n);
                  }
                })(e);
              } finally {
                (f(t), (u = !1));
              }
            }
          }
        }
      })("undefined" == typeof self ? (void 0 === t ? this : t) : self);
    }).call(this, n(9), n(69));
  },
  69: function (t, e) {
    var n,
      i,
      r = (t.exports = {});
    function s() {
      throw new Error("setTimeout has not been defined");
    }
    function o() {
      throw new Error("clearTimeout has not been defined");
    }
    function a(t) {
      if (n === setTimeout) return setTimeout(t, 0);
      if ((n === s || !n) && setTimeout)
        return ((n = setTimeout), setTimeout(t, 0));
      try {
        return n(t, 0);
      } catch (e) {
        try {
          return n.call(null, t, 0);
        } catch (e) {
          return n.call(this, t, 0);
        }
      }
    }
    !(function () {
      try {
        n = "function" == typeof setTimeout ? setTimeout : s;
      } catch (t) {
        n = s;
      }
      try {
        i = "function" == typeof clearTimeout ? clearTimeout : o;
      } catch (t) {
        i = o;
      }
    })();
    var h,
      l = [],
      u = !1,
      c = -1;
    function d() {
      u &&
        h &&
        ((u = !1), h.length ? (l = h.concat(l)) : (c = -1), l.length && f());
    }
    function f() {
      if (!u) {
        var t = a(d);
        u = !0;
        for (var e = l.length; e; ) {
          for (h = l, l = []; ++c < e; ) h && h[c].run();
          ((c = -1), (e = l.length));
        }
        ((h = null),
          (u = !1),
          (function (t) {
            if (i === clearTimeout) return clearTimeout(t);
            if ((i === o || !i) && clearTimeout)
              return ((i = clearTimeout), clearTimeout(t));
            try {
              i(t);
            } catch (e) {
              try {
                return i.call(null, t);
              } catch (e) {
                return i.call(this, t);
              }
            }
          })(t));
      }
    }
    function p(t, e) {
      ((this.fun = t), (this.array = e));
    }
    function g() {}
    ((r.nextTick = function (t) {
      var e = new Array(arguments.length - 1);
      if (arguments.length > 1)
        for (var n = 1; n < arguments.length; n++) e[n - 1] = arguments[n];
      (l.push(new p(t, e)), 1 !== l.length || u || a(f));
    }),
      (p.prototype.run = function () {
        this.fun.apply(null, this.array);
      }),
      (r.title = "browser"),
      (r.browser = !0),
      (r.env = {}),
      (r.argv = []),
      (r.version = ""),
      (r.versions = {}),
      (r.on = g),
      (r.addListener = g),
      (r.once = g),
      (r.off = g),
      (r.removeListener = g),
      (r.removeAllListeners = g),
      (r.emit = g),
      (r.prependListener = g),
      (r.prependOnceListener = g),
      (r.listeners = function (t) {
        return [];
      }),
      (r.binding = function (t) {
        throw new Error("process.binding is not supported");
      }),
      (r.cwd = function () {
        return "/";
      }),
      (r.chdir = function (t) {
        throw new Error("process.chdir is not supported");
      }),
      (r.umask = function () {
        return 0;
      }));
  },
};
