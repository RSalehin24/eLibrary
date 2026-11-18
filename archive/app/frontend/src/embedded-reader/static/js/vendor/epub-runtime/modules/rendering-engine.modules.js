/**
 * Auto-generated from the EPUB runtime source snapshot.
 * Responsibility: Rendition/layout/view managers and annotation pane integration.
 * Module IDs: 10, 11, 12, 13, 14, 15, 16, 17, 53, 54
 */
export const renderingEngineModules = {
  10: function (t, e, n) {
    "use strict";
    var i = n(3),
      r = n.n(i),
      s = n(0),
      o = n(2),
      a = n(14),
      h = n(8),
      l = n(1);
    const u = "undefined" != typeof navigator,
      c = u && /Chrome/.test(navigator.userAgent),
      d = u && !c && /AppleWebKit/.test(navigator.userAgent);
    class f {
      constructor(t, e, n, i) {
        ((this.epubcfi = new o.a()),
          (this.document = t),
          (this.documentElement = this.document.documentElement),
          (this.content = e || this.document.body),
          (this.window = this.document.defaultView),
          (this._size = {
            width: 0,
            height: 0,
          }),
          (this.sectionIndex = i || 0),
          (this.cfiBase = n || ""),
          this.epubReadingSystem("epub.js", l.b),
          (this.called = 0),
          (this.active = !0),
          this.listeners());
      }
      static get listenedEvents() {
        return l.a;
      }
      width(t) {
        var e = this.content;
        return (
          t && Object(s.isNumber)(t) && (t += "px"),
          t && (e.style.width = t),
          parseInt(this.window.getComputedStyle(e).width)
        );
      }
      height(t) {
        var e = this.content;
        return (
          t && Object(s.isNumber)(t) && (t += "px"),
          t && (e.style.height = t),
          parseInt(this.window.getComputedStyle(e).height)
        );
      }
      contentWidth(t) {
        var e = this.content || this.document.body;
        return (
          t && Object(s.isNumber)(t) && (t += "px"),
          t && (e.style.width = t),
          parseInt(this.window.getComputedStyle(e).width)
        );
      }
      contentHeight(t) {
        var e = this.content || this.document.body;
        return (
          t && Object(s.isNumber)(t) && (t += "px"),
          t && (e.style.height = t),
          parseInt(this.window.getComputedStyle(e).height)
        );
      }
      textWidth() {
        let t,
          e,
          n = this.document.createRange(),
          i = this.content || this.document.body,
          r = Object(s.borders)(i);
        return (
          n.selectNodeContents(i),
          (t = n.getBoundingClientRect()),
          (e = t.width),
          r && r.width && (e += r.width),
          Math.round(e)
        );
      }
      textHeight() {
        let t,
          e,
          n = this.document.createRange(),
          i = this.content || this.document.body;
        return (
          n.selectNodeContents(i),
          (t = n.getBoundingClientRect()),
          (e = t.bottom),
          Math.round(e)
        );
      }
      scrollWidth() {
        return this.documentElement.scrollWidth;
      }
      scrollHeight() {
        return this.documentElement.scrollHeight;
      }
      overflow(t) {
        return (
          t && (this.documentElement.style.overflow = t),
          this.window.getComputedStyle(this.documentElement).overflow
        );
      }
      overflowX(t) {
        return (
          t && (this.documentElement.style.overflowX = t),
          this.window.getComputedStyle(this.documentElement).overflowX
        );
      }
      overflowY(t) {
        return (
          t && (this.documentElement.style.overflowY = t),
          this.window.getComputedStyle(this.documentElement).overflowY
        );
      }
      css(t, e, n) {
        var i = this.content || this.document.body;
        return (
          e
            ? i.style.setProperty(t, e, n ? "important" : "")
            : i.style.removeProperty(t),
          this.window.getComputedStyle(i)[t]
        );
      }
      viewport(t) {
        var e,
          n = this.document.querySelector("meta[name='viewport']"),
          i = {
            width: void 0,
            height: void 0,
            scale: void 0,
            minimum: void 0,
            maximum: void 0,
            scalable: void 0,
          },
          r = [];
        if (n && n.hasAttribute("content")) {
          let t = n.getAttribute("content"),
            e = t.match(/width\s*=\s*([^,]*)/),
            r = t.match(/height\s*=\s*([^,]*)/),
            s = t.match(/initial-scale\s*=\s*([^,]*)/),
            o = t.match(/minimum-scale\s*=\s*([^,]*)/),
            a = t.match(/maximum-scale\s*=\s*([^,]*)/),
            h = t.match(/user-scalable\s*=\s*([^,]*)/);
          (e && e.length && void 0 !== e[1] && (i.width = e[1]),
            r && r.length && void 0 !== r[1] && (i.height = r[1]),
            s && s.length && void 0 !== s[1] && (i.scale = s[1]),
            o && o.length && void 0 !== o[1] && (i.minimum = o[1]),
            a && a.length && void 0 !== a[1] && (i.maximum = a[1]),
            h && h.length && void 0 !== h[1] && (i.scalable = h[1]));
        }
        return (
          (e = Object(s.defaults)(t || {}, i)),
          t &&
            (e.width && r.push("width=" + e.width),
            e.height && r.push("height=" + e.height),
            e.scale && r.push("initial-scale=" + e.scale),
            "no" === e.scalable
              ? (r.push("minimum-scale=" + e.scale),
                r.push("maximum-scale=" + e.scale),
                r.push("user-scalable=" + e.scalable))
              : (e.scalable && r.push("user-scalable=" + e.scalable),
                e.minimum && r.push("minimum-scale=" + e.minimum),
                e.maximum && r.push("minimum-scale=" + e.maximum)),
            n ||
              ((n = this.document.createElement("meta")).setAttribute(
                "name",
                "viewport",
              ),
              this.document.querySelector("head").appendChild(n)),
            n.setAttribute("content", r.join(", ")),
            this.window.scrollTo(0, 0)),
          e
        );
      }
      expand() {
        this.emit(l.c.CONTENTS.EXPAND);
      }
      listeners() {
        (this.imageLoadListeners(),
          this.mediaQueryListeners(),
          this.addEventListeners(),
          this.addSelectionListeners(),
          "undefined" == typeof ResizeObserver
            ? (this.resizeListeners(), this.visibilityListeners())
            : this.resizeObservers(),
          this.linksHandler());
      }
      removeListeners() {
        (this.removeEventListeners(),
          this.removeSelectionListeners(),
          this.observer && this.observer.disconnect(),
          clearTimeout(this.expanding));
      }
      resizeCheck() {
        let t = this.textWidth(),
          e = this.textHeight();
        (t == this._size.width && e == this._size.height) ||
          ((this._size = {
            width: t,
            height: e,
          }),
          this.onResize && this.onResize(this._size),
          this.emit(l.c.CONTENTS.RESIZE, this._size));
      }
      resizeListeners() {
        (clearTimeout(this.expanding),
          requestAnimationFrame(this.resizeCheck.bind(this)),
          (this.expanding = setTimeout(this.resizeListeners.bind(this), 350)));
      }
      visibilityListeners() {
        document.addEventListener("visibilitychange", () => {
          "visible" === document.visibilityState && !1 === this.active
            ? ((this.active = !0), this.resizeListeners())
            : ((this.active = !1), clearTimeout(this.expanding));
        });
      }
      transitionListeners() {
        let t = this.content;
        ((t.style.transitionProperty =
          "font, font-size, font-size-adjust, font-stretch, font-variation-settings, font-weight, width, height"),
          (t.style.transitionDuration = "0.001ms"),
          (t.style.transitionTimingFunction = "linear"),
          (t.style.transitionDelay = "0"),
          (this._resizeCheck = this.resizeCheck.bind(this)),
          this.document.addEventListener("transitionend", this._resizeCheck));
      }
      mediaQueryListeners() {
        for (
          var t = this.document.styleSheets,
            e = function (t) {
              t.matches &&
                !this._expanding &&
                setTimeout(this.expand.bind(this), 1);
            }.bind(this),
            n = 0;
          n < t.length;
          n += 1
        ) {
          var i;
          try {
            i = t[n].cssRules;
          } catch (t) {
            return;
          }
          if (!i) return;
          for (var r = 0; r < i.length; r += 1) {
            if (i[r].media)
              this.window.matchMedia(i[r].media.mediaText).addListener(e);
          }
        }
      }
      resizeObservers() {
        ((this.observer = new ResizeObserver((t) => {
          requestAnimationFrame(this.resizeCheck.bind(this));
        })),
          this.observer.observe(this.document.documentElement));
      }
      mutationObservers() {
        this.observer = new MutationObserver((t) => {
          this.resizeCheck();
        });
        this.observer.observe(this.document, {
          attributes: !0,
          childList: !0,
          characterData: !0,
          subtree: !0,
        });
      }
      imageLoadListeners() {
        for (
          var t, e = this.document.querySelectorAll("img"), n = 0;
          n < e.length;
          n++
        )
          void 0 !== (t = e[n]).naturalWidth &&
            0 === t.naturalWidth &&
            (t.onload = this.expand.bind(this));
      }
      fontLoadListeners() {
        this.document &&
          this.document.fonts &&
          this.document.fonts.ready.then(
            function () {
              this.resizeCheck();
            }.bind(this),
          );
      }
      root() {
        return this.document ? this.document.documentElement : null;
      }
      locationOf(t, e) {
        var n,
          i = {
            left: 0,
            top: 0,
          };
        if (!this.document) return i;
        if (this.epubcfi.isCfiString(t)) {
          let r = new o.a(t).toRange(this.document, e);
          if (r) {
            try {
              if (
                !r.endContainer ||
                (r.startContainer == r.endContainer &&
                  r.startOffset == r.endOffset)
              ) {
                let t = r.startContainer.textContent.indexOf(
                  " ",
                  r.startOffset,
                );
                (-1 == t && (t = r.startContainer.textContent.length),
                  r.setEnd(r.startContainer, t));
              }
            } catch (t) {
              console.error(
                "setting end offset to start container length failed",
                t,
              );
            }
            if (r.startContainer.nodeType === Node.ELEMENT_NODE)
              ((n = r.startContainer.getBoundingClientRect()),
                (i.left = n.left),
                (i.top = n.top));
            else if (d) {
              let t = r.startContainer,
                e = new Range();
              try {
                1 === t.nodeType
                  ? (n = t.getBoundingClientRect())
                  : r.startOffset + 2 < t.length
                    ? (e.setStart(t, r.startOffset),
                      e.setEnd(t, r.startOffset + 2),
                      (n = e.getBoundingClientRect()))
                    : r.startOffset - 2 > 0
                      ? (e.setStart(t, r.startOffset - 2),
                        e.setEnd(t, r.startOffset),
                        (n = e.getBoundingClientRect()))
                      : (n = t.parentNode.getBoundingClientRect());
              } catch (t) {
                console.error(t, t.stack);
              }
            } else n = r.getBoundingClientRect();
          }
        } else if ("string" == typeof t && t.indexOf("#") > -1) {
          let e = t.substring(t.indexOf("#") + 1),
            i = this.document.getElementById(e);
          if (i)
            if (d) {
              let t = new Range();
              (t.selectNode(i), (n = t.getBoundingClientRect()));
            } else n = i.getBoundingClientRect();
        }
        return (n && ((i.left = n.left), (i.top = n.top)), i);
      }
      addStylesheet(t) {
        return new Promise(
          function (e, n) {
            var i,
              r = !1;
            this.document
              ? (i = this.document.querySelector("link[href='" + t + "']"))
                ? e(!0)
                : (((i = this.document.createElement("link")).type =
                    "text/css"),
                  (i.rel = "stylesheet"),
                  (i.href = t),
                  (i.onload = i.onreadystatechange =
                    function () {
                      r ||
                        (this.readyState && "complete" != this.readyState) ||
                        ((r = !0),
                        setTimeout(() => {
                          e(!0);
                        }, 1));
                    }),
                  this.document.head.appendChild(i))
              : e(!1);
          }.bind(this),
        );
      }
      _getStylesheetNode(t) {
        var e;
        return (
          (t = "epubjs-inserted-css-" + (t || "")),
          !!this.document &&
            ((e = this.document.getElementById(t)) ||
              (((e = this.document.createElement("style")).id = t),
              this.document.head.appendChild(e)),
            e)
        );
      }
      addStylesheetCss(t, e) {
        return (
          !(!this.document || !t) &&
          ((this._getStylesheetNode(e).innerHTML = t), !0)
        );
      }
      addStylesheetRules(t, e) {
        var n;
        if (this.document && t && 0 !== t.length)
          if (
            ((n = this._getStylesheetNode(e).sheet),
            "[object Array]" === Object.prototype.toString.call(t))
          )
            for (var i = 0, r = t.length; i < r; i++) {
              var s = 1,
                o = t[i],
                a = t[i][0],
                h = "";
              "[object Array]" === Object.prototype.toString.call(o[1][0]) &&
                ((o = o[1]), (s = 0));
              for (var l = o.length; s < l; s++) {
                var u = o[s];
                h += u[0] + ":" + u[1] + (u[2] ? " !important" : "") + ";\n";
              }
              n.insertRule(a + "{" + h + "}", n.cssRules.length);
            }
          else {
            Object.keys(t).forEach((e) => {
              const i = t[e];
              if (Array.isArray(i))
                i.forEach((t) => {
                  const i = Object.keys(t)
                    .map((e) => `${e}:${t[e]}`)
                    .join(";");
                  n.insertRule(`${e}{${i}}`, n.cssRules.length);
                });
              else {
                const t = Object.keys(i)
                  .map((t) => `${t}:${i[t]}`)
                  .join(";");
                n.insertRule(`${e}{${t}}`, n.cssRules.length);
              }
            });
          }
      }
      addScript(t) {
        return new Promise(
          function (e, n) {
            var i,
              r = !1;
            this.document
              ? (((i = this.document.createElement("script")).type =
                  "text/javascript"),
                (i.async = !0),
                (i.src = t),
                (i.onload = i.onreadystatechange =
                  function () {
                    r ||
                      (this.readyState && "complete" != this.readyState) ||
                      ((r = !0),
                      setTimeout(function () {
                        e(!0);
                      }, 1));
                  }),
                this.document.head.appendChild(i))
              : e(!1);
          }.bind(this),
        );
      }
      addClass(t) {
        var e;
        this.document &&
          (e = this.content || this.document.body) &&
          e.classList.add(t);
      }
      removeClass(t) {
        var e;
        this.document &&
          (e = this.content || this.document.body) &&
          e.classList.remove(t);
      }
      addEventListeners() {
        this.document &&
          ((this._triggerEvent = this.triggerEvent.bind(this)),
          l.a.forEach(function (t) {
            this.document.addEventListener(t, this._triggerEvent, {
              passive: !0,
            });
          }, this));
      }
      removeEventListeners() {
        this.document &&
          (l.a.forEach(function (t) {
            this.document.removeEventListener(t, this._triggerEvent, {
              passive: !0,
            });
          }, this),
          (this._triggerEvent = void 0));
      }
      triggerEvent(t) {
        this.emit(t.type, t);
      }
      addSelectionListeners() {
        this.document &&
          ((this._onSelectionChange = this.onSelectionChange.bind(this)),
          this.document.addEventListener(
            "selectionchange",
            this._onSelectionChange,
            {
              passive: !0,
            },
          ));
      }
      removeSelectionListeners() {
        this.document &&
          (this.document.removeEventListener(
            "selectionchange",
            this._onSelectionChange,
            {
              passive: !0,
            },
          ),
          (this._onSelectionChange = void 0));
      }
      onSelectionChange(t) {
        (this.selectionEndTimeout && clearTimeout(this.selectionEndTimeout),
          (this.selectionEndTimeout = setTimeout(
            function () {
              var t = this.window.getSelection();
              this.triggerSelectedEvent(t);
            }.bind(this),
            250,
          )));
      }
      triggerSelectedEvent(t) {
        var e, n;
        t &&
          t.rangeCount > 0 &&
          ((e = t.getRangeAt(0)).collapsed ||
            ((n = new o.a(e, this.cfiBase).toString()),
            this.emit(l.c.CONTENTS.SELECTED, n),
            this.emit(l.c.CONTENTS.SELECTED_RANGE, e)));
      }
      range(t, e) {
        return new o.a(t).toRange(this.document, e);
      }
      cfiFromRange(t, e) {
        return new o.a(t, this.cfiBase, e).toString();
      }
      cfiFromNode(t, e) {
        return new o.a(t, this.cfiBase, e).toString();
      }
      map(t) {
        return new a.a(t).section();
      }
      size(t, e) {
        var n = {
          scale: 1,
          scalable: "no",
        };
        (this.layoutStyle("scrolling"),
          t >= 0 &&
            (this.width(t),
            (n.width = t),
            this.css("padding", "0 " + t / 12 + "px")),
          e >= 0 && (this.height(e), (n.height = e)),
          this.css("margin", "0"),
          this.css("box-sizing", "border-box"),
          this.viewport(n));
      }
      columns(t, e, n, i, r) {
        let o = Object(s.prefixed)("column-axis"),
          a = Object(s.prefixed)("column-gap"),
          h = Object(s.prefixed)("column-width"),
          l = Object(s.prefixed)("column-fill"),
          u =
            0 === this.writingMode().indexOf("vertical")
              ? "vertical"
              : "horizontal";
        (this.layoutStyle("paginated"),
          "rtl" === r && "horizontal" === u && this.direction(r),
          this.width(t),
          this.height(e),
          this.viewport({
            width: t,
            height: e,
            scale: 1,
            scalable: "no",
          }),
          this.css("overflow-y", "hidden"),
          this.css("margin", "0", !0),
          "vertical" === u
            ? (this.css("padding-top", i / 2 + "px", !0),
              this.css("padding-bottom", i / 2 + "px", !0),
              this.css("padding-left", "20px"),
              this.css("padding-right", "20px"),
              this.css(o, "vertical"))
            : (this.css("padding-top", "20px"),
              this.css("padding-bottom", "20px"),
              this.css("padding-left", i / 2 + "px", !0),
              this.css("padding-right", i / 2 + "px", !0),
              this.css(o, "horizontal")),
          this.css("box-sizing", "border-box"),
          this.css("max-width", "inherit"),
          this.css(l, "auto"),
          this.css(a, i + "px"),
          this.css(h, n + "px"),
          this.css("-webkit-line-box-contain", "block glyphs replaced"));
      }
      scaler(t, e, n) {
        var i = "scale(" + t + ")",
          r = "";
        (this.css("transform-origin", "top left"),
          (e >= 0 || n >= 0) &&
            (r = " translate(" + (e || 0) + "px, " + (n || 0) + "px )"),
          this.css("transform", i + r));
      }
      fit(t, e, n) {
        var i = this.viewport(),
          r = parseInt(i.width),
          s = parseInt(i.height),
          o = t / r,
          a = e / s,
          h = o < a ? o : a;
        if (
          (this.layoutStyle("paginated"),
          this.width(r),
          this.height(s),
          this.overflow("hidden"),
          this.scaler(h, 0, 0),
          this.css("background-size", r * h + "px " + s * h + "px"),
          this.css("background-color", "transparent"),
          n && n.properties.includes("page-spread-left"))
        ) {
          var l = t - r * h;
          this.css("margin-left", l + "px");
        }
      }
      direction(t) {
        this.documentElement && (this.documentElement.style.direction = t);
      }
      mapPage(t, e, n, i, r) {
        return new a.a(e, r).page(this, t, n, i);
      }
      linksHandler() {
        Object(h.c)(this.content, (t) => {
          this.emit(l.c.CONTENTS.LINK_CLICKED, t);
        });
      }
      writingMode(t) {
        let e = Object(s.prefixed)("writing-mode");
        return (
          t && this.documentElement && (this.documentElement.style[e] = t),
          this.window.getComputedStyle(this.documentElement)[e] || ""
        );
      }
      layoutStyle(t) {
        return (
          t &&
            ((this._layoutStyle = t),
            (navigator.epubReadingSystem.layoutStyle = this._layoutStyle)),
          this._layoutStyle || "paginated"
        );
      }
      epubReadingSystem(t, e) {
        return (
          (navigator.epubReadingSystem = {
            name: t,
            version: e,
            layoutStyle: this.layoutStyle(),
            hasFeature: function (t) {
              switch (t) {
                case "dom-manipulation":
                case "layout-changes":
                case "touch-events":
                case "mouse-events":
                case "keyboard-events":
                  return !0;
                case "spine-scripting":
                default:
                  return !1;
              }
            },
          }),
          navigator.epubReadingSystem
        );
      }
      destroy() {
        this.removeListeners();
      }
    }
    (r()(f.prototype), (e.a = f));
  },
  11: function (t, e, n) {
    "use strict";
    var i = n(3),
      r = n.n(i),
      s = n(0),
      o = n(6),
      a = n(2),
      h = n(12),
      l = n(17),
      u = n(5);
    var c = class {
        constructor(t) {
          ((this.rendition = t),
            (this._themes = {
              default: {
                rules: {},
                url: "",
                serialized: "",
              },
            }),
            (this._overrides = {}),
            (this._current = "default"),
            (this._injected = []),
            this.rendition.hooks.content.register(this.inject.bind(this)),
            this.rendition.hooks.content.register(this.overrides.bind(this)));
        }
        register() {
          if (0 !== arguments.length)
            return 1 === arguments.length && "object" == typeof arguments[0]
              ? this.registerThemes(arguments[0])
              : 1 === arguments.length && "string" == typeof arguments[0]
                ? this.default(arguments[0])
                : 2 === arguments.length && "string" == typeof arguments[1]
                  ? this.registerUrl(arguments[0], arguments[1])
                  : 2 === arguments.length && "object" == typeof arguments[1]
                    ? this.registerRules(arguments[0], arguments[1])
                    : void 0;
        }
        default(t) {
          if (t)
            return "string" == typeof t
              ? this.registerUrl("default", t)
              : "object" == typeof t
                ? this.registerRules("default", t)
                : void 0;
        }
        registerThemes(t) {
          for (var e in t)
            t.hasOwnProperty(e) &&
              ("string" == typeof t[e]
                ? this.registerUrl(e, t[e])
                : this.registerRules(e, t[e]));
        }
        registerCss(t, e) {
          ((this._themes[t] = {
            serialized: e,
          }),
            (this._injected[t] || "default" == t) && this.update(t));
        }
        registerUrl(t, e) {
          var n = new u.a(e);
          ((this._themes[t] = {
            url: n.toString(),
          }),
            (this._injected[t] || "default" == t) && this.update(t));
        }
        registerRules(t, e) {
          ((this._themes[t] = {
            rules: e,
          }),
            (this._injected[t] || "default" == t) && this.update(t));
        }
        select(t) {
          var e = this._current;
          ((this._current = t),
            this.update(t),
            this.rendition.getContents().forEach((n) => {
              (n.removeClass(e), n.addClass(t));
            }));
        }
        update(t) {
          this.rendition.getContents().forEach((e) => {
            this.add(t, e);
          });
        }
        inject(t) {
          var e,
            n = [],
            i = this._themes;
          for (var r in i)
            !i.hasOwnProperty(r) ||
              (r !== this._current && "default" !== r) ||
              ((((e = i[r]).rules && Object.keys(e.rules).length > 0) ||
                (e.url && -1 === n.indexOf(e.url))) &&
                this.add(r, t),
              this._injected.push(r));
          "default" != this._current && t.addClass(this._current);
        }
        add(t, e) {
          var n = this._themes[t];
          n &&
            e &&
            (n.url
              ? e.addStylesheet(n.url)
              : n.serialized
                ? (e.addStylesheetCss(n.serialized, t), (n.injected = !0))
                : n.rules &&
                  (e.addStylesheetRules(n.rules, t), (n.injected = !0)));
        }
        override(t, e, n) {
          var i = this.rendition.getContents();
          ((this._overrides[t] = {
            value: e,
            priority: !0 === n,
          }),
            i.forEach((e) => {
              e.css(t, this._overrides[t].value, this._overrides[t].priority);
            }));
        }
        removeOverride(t) {
          var e = this.rendition.getContents();
          (delete this._overrides[t],
            e.forEach((e) => {
              e.css(t);
            }));
        }
        overrides(t) {
          var e = this._overrides;
          for (var n in e)
            e.hasOwnProperty(n) && t.css(n, e[n].value, e[n].priority);
        }
        fontSize(t) {
          this.override("font-size", t);
        }
        font(t) {
          this.override("font-family", t, !0);
        }
        destroy() {
          ((this.rendition = void 0),
            (this._themes = void 0),
            (this._overrides = void 0),
            (this._current = void 0),
            (this._injected = void 0));
        }
      },
      d = (n(10), n(1));
    class f {
      constructor({
        type: t,
        cfiRange: e,
        data: n,
        sectionIndex: i,
        cb: r,
        className: s,
        styles: o,
      }) {
        ((this.type = t),
          (this.cfiRange = e),
          (this.data = n),
          (this.sectionIndex = i),
          (this.mark = void 0),
          (this.cb = r),
          (this.className = s),
          (this.styles = o));
      }
      update(t) {
        this.data = t;
      }
      attach(t) {
        let e,
          {
            cfiRange: n,
            data: i,
            type: r,
            mark: s,
            cb: o,
            className: a,
            styles: h,
          } = this;
        return (
          "highlight" === r
            ? (e = t.highlight(n, i, o, a, h))
            : "underline" === r
              ? (e = t.underline(n, i, o, a, h))
              : "mark" === r && (e = t.mark(n, i, o)),
          (this.mark = e),
          this.emit(d.c.ANNOTATION.ATTACH, e),
          e
        );
      }
      detach(t) {
        let e,
          { cfiRange: n, type: i } = this;
        return (
          t &&
            ("highlight" === i
              ? (e = t.unhighlight(n))
              : "underline" === i
                ? (e = t.ununderline(n))
                : "mark" === i && (e = t.unmark(n))),
          (this.mark = void 0),
          this.emit(d.c.ANNOTATION.DETACH, e),
          e
        );
      }
      text() {}
    }
    r()(f.prototype);
    var p = class {
        constructor(t) {
          ((this.rendition = t),
            (this.highlights = []),
            (this.underlines = []),
            (this.marks = []),
            (this._annotations = {}),
            (this._annotationsBySectionIndex = {}),
            this.rendition.hooks.render.register(this.inject.bind(this)),
            this.rendition.hooks.unloaded.register(this.clear.bind(this)));
        }
        add(t, e, n, i, r, s) {
          let o = encodeURI(e + t),
            h = new a.a(e).spinePos,
            l = new f({
              type: t,
              cfiRange: e,
              data: n,
              sectionIndex: h,
              cb: i,
              className: r,
              styles: s,
            });
          return (
            (this._annotations[o] = l),
            h in this._annotationsBySectionIndex
              ? this._annotationsBySectionIndex[h].push(o)
              : (this._annotationsBySectionIndex[h] = [o]),
            this.rendition.views().forEach((t) => {
              l.sectionIndex === t.index && l.attach(t);
            }),
            l
          );
        }
        remove(t, e) {
          let n = encodeURI(t + e);
          if (n in this._annotations) {
            let t = this._annotations[n];
            if (e && t.type !== e) return;
            (this.rendition.views().forEach((e) => {
              (this._removeFromAnnotationBySectionIndex(t.sectionIndex, n),
                t.sectionIndex === e.index && t.detach(e));
            }),
              delete this._annotations[n]);
          }
        }
        _removeFromAnnotationBySectionIndex(t, e) {
          this._annotationsBySectionIndex[t] = this._annotationsAt(t).filter(
            (t) => t !== e,
          );
        }
        _annotationsAt(t) {
          return this._annotationsBySectionIndex[t];
        }
        highlight(t, e, n, i, r) {
          return this.add("highlight", t, e, n, i, r);
        }
        underline(t, e, n, i, r) {
          return this.add("underline", t, e, n, i, r);
        }
        mark(t, e, n) {
          return this.add("mark", t, e, n);
        }
        each() {
          return this._annotations.forEach.apply(this._annotations, arguments);
        }
        inject(t) {
          let e = t.index;
          if (e in this._annotationsBySectionIndex) {
            this._annotationsBySectionIndex[e].forEach((e) => {
              this._annotations[e].attach(t);
            });
          }
        }
        clear(t) {
          let e = t.index;
          if (e in this._annotationsBySectionIndex) {
            this._annotationsBySectionIndex[e].forEach((e) => {
              this._annotations[e].detach(t);
            });
          }
        }
        show() {}
        hide() {}
      },
      g = n(21),
      m = n(13),
      v = n(23);
    class y {
      constructor(t, e) {
        ((this.settings = Object(s.extend)(this.settings || {}, {
          width: null,
          height: null,
          ignoreClass: "",
          manager: "default",
          view: "iframe",
          flow: null,
          layout: null,
          spread: null,
          minSpreadWidth: 800,
          stylesheet: null,
          resizeOnOrientationChange: !0,
          script: null,
          snap: !1,
          defaultDirection: "ltr",
        })),
          Object(s.extend)(this.settings, e),
          "object" == typeof this.settings.manager &&
            (this.manager = this.settings.manager),
          (this.book = t),
          (this.hooks = {}),
          (this.hooks.display = new o.a(this)),
          (this.hooks.serialize = new o.a(this)),
          (this.hooks.content = new o.a(this)),
          (this.hooks.unloaded = new o.a(this)),
          (this.hooks.layout = new o.a(this)),
          (this.hooks.render = new o.a(this)),
          (this.hooks.show = new o.a(this)),
          this.hooks.content.register(this.handleLinks.bind(this)),
          this.hooks.content.register(this.passEvents.bind(this)),
          this.hooks.content.register(this.adjustImages.bind(this)),
          this.book.spine.hooks.content.register(
            this.injectIdentifier.bind(this),
          ),
          this.settings.stylesheet &&
            this.book.spine.hooks.content.register(
              this.injectStylesheet.bind(this),
            ),
          this.settings.script &&
            this.book.spine.hooks.content.register(
              this.injectScript.bind(this),
            ),
          (this.themes = new c(this)),
          (this.annotations = new p(this)),
          (this.epubcfi = new a.a()),
          (this.q = new h.a(this)),
          (this.location = void 0),
          this.q.enqueue(this.book.opened),
          (this.starting = new s.defer()),
          (this.started = this.starting.promise),
          this.q.enqueue(this.start));
      }
      setManager(t) {
        this.manager = t;
      }
      requireManager(t) {
        return "string" == typeof t && "default" === t
          ? m.a
          : "string" == typeof t && "continuous" === t
            ? v.a
            : t;
      }
      requireView(t) {
        return "string" == typeof t && "iframe" === t ? g.a : t;
      }
      start() {
        switch (
          (this.settings.layout ||
            ("pre-paginated" !== this.book.package.metadata.layout &&
              "true" !== this.book.displayOptions.fixedLayout) ||
            (this.settings.layout = "pre-paginated"),
          this.book.package.metadata.spread)
        ) {
          case "none":
            this.settings.spread = "none";
            break;
          case "both":
            this.settings.spread = !0;
        }
        (this.manager ||
          ((this.ViewManager = this.requireManager(this.settings.manager)),
          (this.View = this.requireView(this.settings.view)),
          (this.manager = new this.ViewManager({
            view: this.View,
            queue: this.q,
            request: this.book.load.bind(this.book),
            settings: this.settings,
          }))),
          this.direction(
            this.book.package.metadata.direction ||
              this.settings.defaultDirection,
          ),
          (this.settings.globalLayoutProperties =
            this.determineLayoutProperties(this.book.package.metadata)),
          this.flow(this.settings.globalLayoutProperties.flow),
          this.layout(this.settings.globalLayoutProperties),
          this.manager.on(d.c.MANAGERS.ADDED, this.afterDisplayed.bind(this)),
          this.manager.on(d.c.MANAGERS.REMOVED, this.afterRemoved.bind(this)),
          this.manager.on(d.c.MANAGERS.RESIZED, this.onResized.bind(this)),
          this.manager.on(
            d.c.MANAGERS.ORIENTATION_CHANGE,
            this.onOrientationChange.bind(this),
          ),
          this.manager.on(
            d.c.MANAGERS.SCROLLED,
            this.reportLocation.bind(this),
          ),
          this.emit(d.c.RENDITION.STARTED),
          this.starting.resolve());
      }
      attachTo(t) {
        return this.q.enqueue(
          function () {
            (this.manager.render(t, {
              width: this.settings.width,
              height: this.settings.height,
            }),
              this.emit(d.c.RENDITION.ATTACHED));
          }.bind(this),
        );
      }
      display(t) {
        return (
          this.displaying && this.displaying.resolve(),
          this.q.enqueue(this._display, t)
        );
      }
      _display(t) {
        if (this.book) {
          this.epubcfi.isCfiString(t);
          var e,
            n = new s.defer(),
            i = n.promise;
          return (
            (this.displaying = n),
            this.book.locations.length() &&
              Object(s.isFloat)(t) &&
              (t = this.book.locations.cfiFromPercentage(parseFloat(t))),
            (e = this.book.spine.get(t))
              ? (this.manager.display(e, t).then(
                  () => {
                    (n.resolve(e),
                      (this.displaying = void 0),
                      this.emit(d.c.RENDITION.DISPLAYED, e),
                      this.reportLocation());
                  },
                  (t) => {
                    this.emit(d.c.RENDITION.DISPLAY_ERROR, t);
                  },
                ),
                i)
              : (n.reject(new Error("No Section Found")), i)
          );
        }
      }
      afterDisplayed(t) {
        (t.on(d.c.VIEWS.MARK_CLICKED, (e, n) =>
          this.triggerMarkEvent(e, n, t.contents),
        ),
          this.hooks.render.trigger(t, this).then(() => {
            t.contents
              ? this.hooks.content.trigger(t.contents, this).then(() => {
                  this.emit(d.c.RENDITION.RENDERED, t.section, t);
                })
              : this.emit(d.c.RENDITION.RENDERED, t.section, t);
          }));
      }
      afterRemoved(t) {
        this.hooks.unloaded.trigger(t, this).then(() => {
          this.emit(d.c.RENDITION.REMOVED, t.section, t);
        });
      }
      onResized(t, e) {
        (this.emit(
          d.c.RENDITION.RESIZED,
          {
            width: t.width,
            height: t.height,
          },
          e,
        ),
          this.location &&
            this.location.start &&
            this.display(e || this.location.start.cfi));
      }
      onOrientationChange(t) {
        this.emit(d.c.RENDITION.ORIENTATION_CHANGE, t);
      }
      moveTo(t) {
        this.manager.moveTo(t);
      }
      resize(t, e, n) {
        (t && (this.settings.width = t),
          e && (this.settings.height = e),
          this.manager.resize(t, e, n));
      }
      clear() {
        this.manager.clear();
      }
      next() {
        return this.q
          .enqueue(this.manager.next.bind(this.manager))
          .then(this.reportLocation.bind(this));
      }
      prev() {
        return this.q
          .enqueue(this.manager.prev.bind(this.manager))
          .then(this.reportLocation.bind(this));
      }
      determineLayoutProperties(t) {
        var e = this.settings.layout || t.layout || "reflowable",
          n = this.settings.spread || t.spread || "auto",
          i = this.settings.orientation || t.orientation || "auto",
          r = this.settings.flow || t.flow || "auto",
          s = t.viewport || "",
          o = this.settings.minSpreadWidth || t.minSpreadWidth || 800,
          a = this.settings.direction || t.direction || "ltr";
        return (
          (0 === this.settings.width || this.settings.width > 0) &&
            (0 === this.settings.height || this.settings.height),
          {
            layout: e,
            spread: n,
            orientation: i,
            flow: r,
            viewport: s,
            minSpreadWidth: o,
            direction: a,
          }
        );
      }
      flow(t) {
        var e = t;
        (("scrolled" !== t &&
          "scrolled-doc" !== t &&
          "scrolled-continuous" !== t) ||
          (e = "scrolled"),
          ("auto" !== t && "paginated" !== t) || (e = "paginated"),
          (this.settings.flow = t),
          this._layout && this._layout.flow(e),
          this.manager &&
            this._layout &&
            this.manager.applyLayout(this._layout),
          this.manager && this.manager.updateFlow(e),
          this.manager &&
            this.manager.isRendered() &&
            this.location &&
            (this.manager.clear(), this.display(this.location.start.cfi)));
      }
      layout(t) {
        return (
          t &&
            ((this._layout = new l.a(t)),
            this._layout.spread(t.spread, this.settings.minSpreadWidth),
            this._layout.on(d.c.LAYOUT.UPDATED, (t, e) => {
              this.emit(d.c.RENDITION.LAYOUT, t, e);
            })),
          this.manager &&
            this._layout &&
            this.manager.applyLayout(this._layout),
          this._layout
        );
      }
      spread(t, e) {
        ((this.settings.spread = t),
          e && (this.settings.minSpreadWidth = e),
          this._layout && this._layout.spread(t, e),
          this.manager &&
            this.manager.isRendered() &&
            this.manager.updateLayout());
      }
      direction(t) {
        ((this.settings.direction = t || "ltr"),
          this.manager && this.manager.direction(this.settings.direction),
          this.manager &&
            this.manager.isRendered() &&
            this.location &&
            (this.manager.clear(), this.display(this.location.start.cfi)));
      }
      reportLocation() {
        return this.q.enqueue(
          function () {
            requestAnimationFrame(
              function () {
                var t = this.manager.currentLocation();
                if (t && t.then && "function" == typeof t.then)
                  t.then(
                    function (t) {
                      let e = this.located(t);
                      e &&
                        e.start &&
                        e.end &&
                        ((this.location = e),
                        this.emit(d.c.RENDITION.LOCATION_CHANGED, {
                          index: this.location.start.index,
                          href: this.location.start.href,
                          start: this.location.start.cfi,
                          end: this.location.end.cfi,
                          percentage: this.location.start.percentage,
                        }),
                        this.emit(d.c.RENDITION.RELOCATED, this.location));
                    }.bind(this),
                  );
                else if (t) {
                  let e = this.located(t);
                  if (!e || !e.start || !e.end) return;
                  ((this.location = e),
                    this.emit(d.c.RENDITION.LOCATION_CHANGED, {
                      index: this.location.start.index,
                      href: this.location.start.href,
                      start: this.location.start.cfi,
                      end: this.location.end.cfi,
                      percentage: this.location.start.percentage,
                    }),
                    this.emit(d.c.RENDITION.RELOCATED, this.location));
                }
              }.bind(this),
            );
          }.bind(this),
        );
      }
      currentLocation() {
        var t = this.manager.currentLocation();
        if (t && t.then && "function" == typeof t.then)
          t.then(
            function (t) {
              return this.located(t);
            }.bind(this),
          );
        else if (t) {
          return this.located(t);
        }
      }
      located(t) {
        if (!t.length) return {};
        let e = t[0],
          n = t[t.length - 1],
          i = {
            start: {
              index: e.index,
              href: e.href,
              cfi: e.mapping.start,
              displayed: {
                page: e.pages[0] || 1,
                total: e.totalPages,
              },
            },
            end: {
              index: n.index,
              href: n.href,
              cfi: n.mapping.end,
              displayed: {
                page: n.pages[n.pages.length - 1] || 1,
                total: n.totalPages,
              },
            },
          },
          r = this.book.locations.locationFromCfi(e.mapping.start),
          s = this.book.locations.locationFromCfi(n.mapping.end);
        (null != r &&
          ((i.start.location = r),
          (i.start.percentage = this.book.locations.percentageFromLocation(r))),
          null != s &&
            ((i.end.location = s),
            (i.end.percentage =
              this.book.locations.percentageFromLocation(s))));
        let o = this.book.pageList.pageFromCfi(e.mapping.start),
          a = this.book.pageList.pageFromCfi(n.mapping.end);
        return (
          -1 != o && (i.start.page = o),
          -1 != a && (i.end.page = a),
          n.index === this.book.spine.last().index &&
            i.end.displayed.page >= i.end.displayed.total &&
            (i.atEnd = !0),
          e.index === this.book.spine.first().index &&
            1 === i.start.displayed.page &&
            (i.atStart = !0),
          i
        );
      }
      destroy() {
        (this.manager && this.manager.destroy(), (this.book = void 0));
      }
      passEvents(t) {
        (d.a.forEach((e) => {
          t.on(e, (e) => this.triggerViewEvent(e, t));
        }),
          t.on(d.c.CONTENTS.SELECTED, (e) => this.triggerSelectedEvent(e, t)));
      }
      triggerViewEvent(t, e) {
        this.emit(t.type, t, e);
      }
      triggerSelectedEvent(t, e) {
        this.emit(d.c.RENDITION.SELECTED, t, e);
      }
      triggerMarkEvent(t, e, n) {
        this.emit(d.c.RENDITION.MARK_CLICKED, t, e, n);
      }
      getRange(t, e) {
        var n = new a.a(t),
          i = this.manager.visible().filter(function (t) {
            if (n.spinePos === t.index) return !0;
          });
        if (i.length) return i[0].contents.range(n, e);
      }
      adjustImages(t) {
        if ("pre-paginated" === this._layout.name)
          return new Promise(function (t) {
            t();
          });
        let e = t.window.getComputedStyle(t.content, null),
          n =
            0.95 *
            (t.content.offsetHeight -
              (parseFloat(e.paddingTop) + parseFloat(e.paddingBottom))),
          i = parseFloat(e.paddingLeft) + parseFloat(e.paddingRight);
        return (
          t.addStylesheetRules({
            img: {
              "max-width":
                (this._layout.columnWidth
                  ? this._layout.columnWidth - i + "px"
                  : "100%") + "!important",
              "max-height": n + "px!important",
              "object-fit": "contain",
              "page-break-inside": "avoid",
              "break-inside": "avoid",
              "box-sizing": "border-box",
            },
            svg: {
              "max-width":
                (this._layout.columnWidth
                  ? this._layout.columnWidth - i + "px"
                  : "100%") + "!important",
              "max-height": n + "px!important",
              "page-break-inside": "avoid",
              "break-inside": "avoid",
            },
          }),
          new Promise(function (t, e) {
            setTimeout(function () {
              t();
            }, 1);
          })
        );
      }
      getContents() {
        return this.manager ? this.manager.getContents() : [];
      }
      views() {
        return (this.manager ? this.manager.views : void 0) || [];
      }
      handleLinks(t) {
        t &&
          t.on(d.c.CONTENTS.LINK_CLICKED, (t) => {
            let e = this.book.path.relative(t);
            this.display(e);
          });
      }
      injectStylesheet(t, e) {
        let n = t.createElement("link");
        (n.setAttribute("type", "text/css"),
          n.setAttribute("rel", "stylesheet"),
          n.setAttribute("href", this.settings.stylesheet),
          t.getElementsByTagName("head")[0].appendChild(n));
      }
      injectScript(t, e) {
        let n = t.createElement("script");
        (n.setAttribute("type", "text/javascript"),
          n.setAttribute("src", this.settings.script),
          (n.textContent = " "),
          t.getElementsByTagName("head")[0].appendChild(n));
      }
      injectIdentifier(t, e) {
        let n = this.book.packaging.metadata.identifier,
          i = t.createElement("meta");
        (i.setAttribute("name", "dc.relation.ispartof"),
          n && i.setAttribute("content", n),
          t.getElementsByTagName("head")[0].appendChild(i));
      }
    }
    r()(y.prototype);
    e.a = y;
  },
  12: function (t, e, n) {
    "use strict";
    var i = n(0);
    e.a = class {
      constructor(t) {
        ((this._q = []),
          (this.context = t),
          (this.tick = i.requestAnimationFrame),
          (this.running = !1),
          (this.paused = !1));
      }
      enqueue() {
        var t,
          e,
          n = [].shift.call(arguments),
          r = arguments;
        if (!n) throw new Error("No Task Provided");
        return (
          (e =
            "function" == typeof n
              ? {
                  task: n,
                  args: r,
                  deferred: (t = new i.defer()),
                  promise: t.promise,
                }
              : {
                  promise: n,
                }),
          this._q.push(e),
          0 != this.paused || this.running || this.run(),
          e.promise
        );
      }
      dequeue() {
        var t, e, n;
        return !this._q.length || this.paused
          ? ((t = new i.defer()).deferred.resolve(), t.promise)
          : (e = (t = this._q.shift()).task)
            ? (n = e.apply(this.context, t.args)) && "function" == typeof n.then
              ? n.then(
                  function () {
                    t.deferred.resolve.apply(this.context, arguments);
                  }.bind(this),
                  function () {
                    t.deferred.reject.apply(this.context, arguments);
                  }.bind(this),
                )
              : (t.deferred.resolve.apply(this.context, n), t.promise)
            : t.promise
              ? t.promise
              : void 0;
      }
      dump() {
        for (; this._q.length; ) this.dequeue();
      }
      run() {
        return (
          this.running || ((this.running = !0), (this.defered = new i.defer())),
          this.tick.call(window, () => {
            this._q.length
              ? this.dequeue().then(
                  function () {
                    this.run();
                  }.bind(this),
                )
              : (this.defered.resolve(), (this.running = void 0));
          }),
          1 == this.paused && (this.paused = !1),
          this.defered.promise
        );
      }
      flush() {
        return this.running
          ? this.running
          : this._q.length
            ? ((this.running = this.dequeue().then(
                function () {
                  return ((this.running = void 0), this.flush());
                }.bind(this),
              )),
              this.running)
            : void 0;
      }
      clear() {
        this._q = [];
      }
      length() {
        return this._q.length;
      }
      pause() {
        this.paused = !0;
      }
      stop() {
        ((this._q = []), (this.running = !1), (this.paused = !0));
      }
    };
  },
  13: function (t, e, n) {
    "use strict";
    var i = n(3),
      r = n.n(i),
      s = n(0);
    function o() {
      var t = "reverse",
        e = (function () {
          var t = document.createElement("div");
          ((t.dir = "rtl"),
            (t.style.position = "fixed"),
            (t.style.width = "1px"),
            (t.style.height = "1px"),
            (t.style.top = "0px"),
            (t.style.left = "0px"),
            (t.style.overflow = "hidden"));
          var e = document.createElement("div");
          e.style.width = "2px";
          var n = document.createElement("span");
          ((n.style.width = "1px"), (n.style.display = "inline-block"));
          var i = document.createElement("span");
          return (
            (i.style.width = "1px"),
            (i.style.display = "inline-block"),
            e.appendChild(n),
            e.appendChild(i),
            t.appendChild(e),
            t
          );
        })();
      return (
        document.body.appendChild(e),
        e.scrollLeft > 0
          ? (t = "default")
          : "undefined" != typeof Element && Element.prototype.scrollIntoView
            ? (e.children[0].children[1].scrollIntoView(),
              e.scrollLeft < 0 && (t = "negative"))
            : ((e.scrollLeft = 1), 0 === e.scrollLeft && (t = "negative")),
        document.body.removeChild(e),
        t
      );
    }
    var a = n(14),
      h = n(12),
      l = n(30),
      u = n.n(l);
    var c = class {
      constructor(t) {
        ((this.settings = t || {}),
          (this.id = "epubjs-container-" + Object(s.uuid)()),
          (this.container = this.create(this.settings)),
          this.settings.hidden && (this.wrapper = this.wrap(this.container)));
      }
      create(t) {
        let e = t.height,
          n = t.width,
          i = t.overflow || !1,
          r = t.axis || "vertical",
          o = t.direction;
        (Object(s.extend)(this.settings, t),
          t.height && Object(s.isNumber)(t.height) && (e = t.height + "px"),
          t.width && Object(s.isNumber)(t.width) && (n = t.width + "px"));
        let a = document.createElement("div");
        return (
          (a.id = this.id),
          a.classList.add("epub-container"),
          (a.style.wordSpacing = "0"),
          (a.style.lineHeight = "0"),
          (a.style.verticalAlign = "top"),
          (a.style.position = "relative"),
          "horizontal" === r &&
            ((a.style.display = "flex"),
            (a.style.flexDirection = "row"),
            (a.style.flexWrap = "nowrap")),
          n && (a.style.width = n),
          e && (a.style.height = e),
          i &&
            ("scroll" === i && "vertical" === r
              ? ((a.style["overflow-y"] = i),
                (a.style["overflow-x"] = "hidden"))
              : "scroll" === i && "horizontal" === r
                ? ((a.style["overflow-y"] = "hidden"),
                  (a.style["overflow-x"] = i))
                : (a.style.overflow = i)),
          o && ((a.dir = o), (a.style.direction = o)),
          o && this.settings.fullsize && (document.body.style.direction = o),
          a
        );
      }
      wrap(t) {
        var e = document.createElement("div");
        return (
          (e.style.visibility = "hidden"),
          (e.style.overflow = "hidden"),
          (e.style.width = "0"),
          (e.style.height = "0"),
          e.appendChild(t),
          e
        );
      }
      getElement(t) {
        var e;
        if (
          (Object(s.isElement)(t)
            ? (e = t)
            : "string" == typeof t && (e = document.getElementById(t)),
          !e)
        )
          throw new Error("Not an Element");
        return e;
      }
      attachTo(t) {
        var e,
          n = this.getElement(t);
        if (n)
          return (
            (e = this.settings.hidden ? this.wrapper : this.container),
            n.appendChild(e),
            (this.element = n),
            n
          );
      }
      getContainer() {
        return this.container;
      }
      onResize(t) {
        (Object(s.isNumber)(this.settings.width) &&
          Object(s.isNumber)(this.settings.height)) ||
          ((this.resizeFunc = u()(t, 50)),
          window.addEventListener("resize", this.resizeFunc, !1));
      }
      onOrientationChange(t) {
        ((this.orientationChangeFunc = t),
          window.addEventListener(
            "orientationchange",
            this.orientationChangeFunc,
            !1,
          ));
      }
      size(t, e) {
        var n;
        let i = t || this.settings.width,
          r = e || this.settings.height;
        (null === t
          ? (n = this.element.getBoundingClientRect()).width &&
            ((t = Math.floor(n.width)), (this.container.style.width = t + "px"))
          : Object(s.isNumber)(t)
            ? (this.container.style.width = t + "px")
            : (this.container.style.width = t),
          null === e
            ? (n = n || this.element.getBoundingClientRect()).height &&
              ((e = n.height), (this.container.style.height = e + "px"))
            : Object(s.isNumber)(e)
              ? (this.container.style.height = e + "px")
              : (this.container.style.height = e),
          Object(s.isNumber)(t) || (t = this.container.clientWidth),
          Object(s.isNumber)(e) || (e = this.container.clientHeight),
          (this.containerStyles = window.getComputedStyle(this.container)),
          (this.containerPadding = {
            left: parseFloat(this.containerStyles["padding-left"]) || 0,
            right: parseFloat(this.containerStyles["padding-right"]) || 0,
            top: parseFloat(this.containerStyles["padding-top"]) || 0,
            bottom: parseFloat(this.containerStyles["padding-bottom"]) || 0,
          }));
        let o = Object(s.windowBounds)(),
          a = window.getComputedStyle(document.body),
          h = parseFloat(a["padding-left"]) || 0,
          l = parseFloat(a["padding-right"]) || 0,
          u = parseFloat(a["padding-top"]) || 0,
          c = parseFloat(a["padding-bottom"]) || 0;
        return (
          i || (t = o.width - h - l),
          ((this.settings.fullsize && !r) || !r) && (e = o.height - u - c),
          {
            width: t - this.containerPadding.left - this.containerPadding.right,
            height:
              e - this.containerPadding.top - this.containerPadding.bottom,
          }
        );
      }
      bounds() {
        let t;
        return (
          "visible" !== this.container.style.overflow &&
            (t = this.container && this.container.getBoundingClientRect()),
          t && t.width && t.height ? t : Object(s.windowBounds)()
        );
      }
      getSheet() {
        var t = document.createElement("style");
        return (
          t.appendChild(document.createTextNode("")),
          document.head.appendChild(t),
          t.sheet
        );
      }
      addStyleRules(t, e) {
        var n = "#" + this.id + " ",
          i = "";
        (this.sheet || (this.sheet = this.getSheet()),
          e.forEach(function (t) {
            for (var e in t) t.hasOwnProperty(e) && (i += e + ":" + t[e] + ";");
          }),
          this.sheet.insertRule(n + t + " {" + i + "}", 0));
      }
      axis(t) {
        ("horizontal" === t
          ? ((this.container.style.display = "flex"),
            (this.container.style.flexDirection = "row"),
            (this.container.style.flexWrap = "nowrap"))
          : (this.container.style.display = "block"),
          (this.settings.axis = t));
      }
      direction(t) {
        (this.container &&
          ((this.container.dir = t), (this.container.style.direction = t)),
          this.settings.fullsize && (document.body.style.direction = t),
          (this.settings.dir = t));
      }
      overflow(t) {
        (this.container &&
          ("scroll" === t && "vertical" === this.settings.axis
            ? ((this.container.style["overflow-y"] = t),
              (this.container.style["overflow-x"] = "hidden"))
            : "scroll" === t && "horizontal" === this.settings.axis
              ? ((this.container.style["overflow-y"] = "hidden"),
                (this.container.style["overflow-x"] = t))
              : (this.container.style.overflow = t)),
          (this.settings.overflow = t));
      }
      destroy() {
        this.element &&
          (this.settings.hidden ? this.wrapper : this.container,
          this.element.contains(this.container) &&
            this.element.removeChild(this.container),
          window.removeEventListener("resize", this.resizeFunc),
          window.removeEventListener(
            "orientationChange",
            this.orientationChangeFunc,
          ));
      }
    };
    var d = class {
        constructor(t) {
          ((this.container = t),
            (this._views = []),
            (this.length = 0),
            (this.hidden = !1));
        }
        all() {
          return this._views;
        }
        first() {
          return this._views[0];
        }
        last() {
          return this._views[this._views.length - 1];
        }
        indexOf(t) {
          return this._views.indexOf(t);
        }
        slice() {
          return this._views.slice.apply(this._views, arguments);
        }
        get(t) {
          return this._views[t];
        }
        append(t) {
          return (
            this._views.push(t),
            this.container && this.container.appendChild(t.element),
            this.length++,
            t
          );
        }
        prepend(t) {
          return (
            this._views.unshift(t),
            this.container &&
              this.container.insertBefore(t.element, this.container.firstChild),
            this.length++,
            t
          );
        }
        insert(t, e) {
          return (
            this._views.splice(e, 0, t),
            this.container &&
              (e < this.container.children.length
                ? this.container.insertBefore(
                    t.element,
                    this.container.children[e],
                  )
                : this.container.appendChild(t.element)),
            this.length++,
            t
          );
        }
        remove(t) {
          var e = this._views.indexOf(t);
          (e > -1 && this._views.splice(e, 1), this.destroy(t), this.length--);
        }
        destroy(t) {
          (t.displayed && t.destroy(),
            this.container && this.container.removeChild(t.element),
            (t = null));
        }
        forEach() {
          return this._views.forEach.apply(this._views, arguments);
        }
        clear() {
          var t,
            e = this.length;
          if (this.length) {
            for (var n = 0; n < e; n++) ((t = this._views[n]), this.destroy(t));
            ((this._views = []), (this.length = 0));
          }
        }
        find(t) {
          for (var e, n = this.length, i = 0; i < n; i++)
            if ((e = this._views[i]).displayed && e.section.index == t.index)
              return e;
        }
        displayed() {
          for (var t, e = [], n = this.length, i = 0; i < n; i++)
            (t = this._views[i]).displayed && e.push(t);
          return e;
        }
        show() {
          for (var t, e = this.length, n = 0; n < e; n++)
            (t = this._views[n]).displayed && t.show();
          this.hidden = !1;
        }
        hide() {
          for (var t, e = this.length, n = 0; n < e; n++)
            (t = this._views[n]).displayed && t.hide();
          this.hidden = !0;
        }
      },
      f = n(1);
    class p {
      constructor(t) {
        ((this.name = "default"),
          (this.optsSettings = t.settings),
          (this.View = t.view),
          (this.request = t.request),
          (this.renditionQueue = t.queue),
          (this.q = new h.a(this)),
          (this.settings = Object(s.extend)(this.settings || {}, {
            infinite: !0,
            hidden: !1,
            width: void 0,
            height: void 0,
            axis: void 0,
            writingMode: void 0,
            flow: "scrolled",
            ignoreClass: "",
            fullsize: void 0,
          })),
          Object(s.extend)(this.settings, t.settings || {}),
          (this.viewSettings = {
            ignoreClass: this.settings.ignoreClass,
            axis: this.settings.axis,
            flow: this.settings.flow,
            layout: this.layout,
            method: this.settings.method,
            width: 0,
            height: 0,
            forceEvenPages: !0,
          }),
          (this.rendered = !1));
      }
      render(t, e) {
        let n = t.tagName;
        (void 0 !== this.settings.fullsize ||
          !n ||
          ("body" != n.toLowerCase() && "html" != n.toLowerCase()) ||
          (this.settings.fullsize = !0),
          this.settings.fullsize &&
            ((this.settings.overflow = "visible"),
            (this.overflow = this.settings.overflow)),
          (this.settings.size = e),
          (this.settings.rtlScrollType = o()),
          (this.stage = new c({
            width: e.width,
            height: e.height,
            overflow: this.overflow,
            hidden: this.settings.hidden,
            axis: this.settings.axis,
            fullsize: this.settings.fullsize,
            direction: this.settings.direction,
          })),
          this.stage.attachTo(t),
          (this.container = this.stage.getContainer()),
          (this.views = new d(this.container)),
          (this._bounds = this.bounds()),
          (this._stageSize = this.stage.size()),
          (this.viewSettings.width = this._stageSize.width),
          (this.viewSettings.height = this._stageSize.height),
          this.stage.onResize(this.onResized.bind(this)),
          this.stage.onOrientationChange(this.onOrientationChange.bind(this)),
          this.addEventListeners(),
          this.layout && this.updateLayout(),
          (this.rendered = !0));
      }
      addEventListeners() {
        var t;
        ((this._onPageHide = function () {
          this.destroy();
        }.bind(this)),
          window.addEventListener("pagehide", this._onPageHide),
          (t = this.settings.fullsize ? window : this.container),
          (this._onScroll = this.onScroll.bind(this)),
          t.addEventListener("scroll", this._onScroll));
      }
      removeEventListeners() {
        ((this.settings.fullsize ? window : this.container).removeEventListener(
          "scroll",
          this._onScroll,
        ),
          (this._onScroll = void 0),
          this._onPageHide &&
            (window.removeEventListener("pagehide", this._onPageHide),
            (this._onPageHide = void 0)));
      }
      destroy() {
        (clearTimeout(this.orientationTimeout),
          clearTimeout(this.resizeTimeout),
          clearTimeout(this.afterScrolled),
          this.clear(),
          this.removeEventListeners(),
          this.stage.destroy(),
          (this.rendered = !1));
      }
      onOrientationChange(t) {
        let { orientation: e } = window;
        (this.optsSettings.resizeOnOrientationChange && this.resize(),
          clearTimeout(this.orientationTimeout),
          (this.orientationTimeout = setTimeout(
            function () {
              ((this.orientationTimeout = void 0),
                this.optsSettings.resizeOnOrientationChange && this.resize(),
                this.emit(f.c.MANAGERS.ORIENTATION_CHANGE, e));
            }.bind(this),
            500,
          )));
      }
      onResized(t) {
        this.resize();
      }
      resize(t, e, n) {
        let i = this.stage.size(t, e);
        ((this.winBounds = Object(s.windowBounds)()),
          this.orientationTimeout &&
          this.winBounds.width === this.winBounds.height
            ? (this._stageSize = void 0)
            : (this._stageSize &&
                this._stageSize.width === i.width &&
                this._stageSize.height === i.height) ||
              ((this._stageSize = i),
              (this._bounds = this.bounds()),
              this.clear(),
              (this.viewSettings.width = this._stageSize.width),
              (this.viewSettings.height = this._stageSize.height),
              this.updateLayout(),
              this.emit(
                f.c.MANAGERS.RESIZED,
                {
                  width: this._stageSize.width,
                  height: this._stageSize.height,
                },
                n,
              )));
      }
      createView(t, e) {
        return new this.View(
          t,
          Object(s.extend)(this.viewSettings, {
            forceRight: e,
          }),
        );
      }
      handleNextPrePaginated(t, e, n) {
        let i;
        if ("pre-paginated" === this.layout.name && this.layout.divisor > 1) {
          if (t || 0 === e.index) return;
          if (((i = e.next()), i && !i.properties.includes("page-spread-left")))
            return n.call(this, i);
        }
      }
      display(t, e) {
        var n = new s.defer(),
          i = n.promise;
        (e === t.href || Object(s.isNumber)(e)) && (e = void 0);
        var r = this.views.find(t);
        if (r && t && "pre-paginated" !== this.layout.name) {
          let t = r.offset();
          if ("ltr" === this.settings.direction)
            this.scrollTo(t.left, t.top, !0);
          else {
            let e = r.width();
            this.scrollTo(t.left + e, t.top, !0);
          }
          if (e) {
            let t = r.locationOf(e);
            this.moveTo(t);
          }
          return (n.resolve(), i);
        }
        this.clear();
        let o = !1;
        return (
          "pre-paginated" === this.layout.name &&
            2 === this.layout.divisor &&
            t.properties.includes("page-spread-right") &&
            (o = !0),
          this.add(t, o)
            .then(
              function (t) {
                if (e) {
                  let n = t.locationOf(e);
                  this.moveTo(n);
                }
              }.bind(this),
              (t) => {
                n.reject(t);
              },
            )
            .then(
              function () {
                return this.handleNextPrePaginated(o, t, this.add);
              }.bind(this),
            )
            .then(
              function () {
                (this.views.show(), n.resolve());
              }.bind(this),
            ),
          i
        );
      }
      afterDisplayed(t) {
        this.emit(f.c.MANAGERS.ADDED, t);
      }
      afterResized(t) {
        this.emit(f.c.MANAGERS.RESIZE, t.section);
      }
      moveTo(t) {
        var e = 0,
          n = 0;
        (this.isPaginated
          ? (e = Math.floor(t.left / this.layout.delta) * this.layout.delta) +
              this.layout.delta >
              this.container.scrollWidth &&
            (e = this.container.scrollWidth - this.layout.delta)
          : (n = t.top),
          this.scrollTo(e, n, !0));
      }
      add(t, e) {
        var n = this.createView(t, e);
        return (
          this.views.append(n),
          (n.onDisplayed = this.afterDisplayed.bind(this)),
          (n.onResize = this.afterResized.bind(this)),
          n.on(f.c.VIEWS.AXIS, (t) => {
            this.updateAxis(t);
          }),
          n.on(f.c.VIEWS.WRITING_MODE, (t) => {
            this.updateWritingMode(t);
          }),
          n.display(this.request)
        );
      }
      append(t, e) {
        var n = this.createView(t, e);
        return (
          this.views.append(n),
          (n.onDisplayed = this.afterDisplayed.bind(this)),
          (n.onResize = this.afterResized.bind(this)),
          n.on(f.c.VIEWS.AXIS, (t) => {
            this.updateAxis(t);
          }),
          n.on(f.c.VIEWS.WRITING_MODE, (t) => {
            this.updateWritingMode(t);
          }),
          n.display(this.request)
        );
      }
      prepend(t, e) {
        var n = this.createView(t, e);
        return (
          n.on(f.c.VIEWS.RESIZED, (t) => {
            this.counter(t);
          }),
          this.views.prepend(n),
          (n.onDisplayed = this.afterDisplayed.bind(this)),
          (n.onResize = this.afterResized.bind(this)),
          n.on(f.c.VIEWS.AXIS, (t) => {
            this.updateAxis(t);
          }),
          n.on(f.c.VIEWS.WRITING_MODE, (t) => {
            this.updateWritingMode(t);
          }),
          n.display(this.request)
        );
      }
      counter(t) {
        "vertical" === this.settings.axis
          ? this.scrollBy(0, t.heightDelta, !0)
          : this.scrollBy(t.widthDelta, 0, !0);
      }
      next() {
        var t;
        let e = this.settings.direction;
        if (this.views.length) {
          if (
            !this.isPaginated ||
            "horizontal" !== this.settings.axis ||
            (e && "ltr" !== e)
          )
            if (
              this.isPaginated &&
              "horizontal" === this.settings.axis &&
              "rtl" === e
            )
              ((this.scrollLeft = this.container.scrollLeft),
                "default" === this.settings.rtlScrollType
                  ? this.container.scrollLeft > 0
                    ? this.scrollBy(this.layout.delta, 0, !0)
                    : (t = this.views.last().section.next())
                  : this.container.scrollLeft + -1 * this.layout.delta >
                      -1 * this.container.scrollWidth
                    ? this.scrollBy(this.layout.delta, 0, !0)
                    : (t = this.views.last().section.next()));
            else if (this.isPaginated && "vertical" === this.settings.axis) {
              ((this.scrollTop = this.container.scrollTop),
                this.container.scrollTop + this.container.offsetHeight <
                this.container.scrollHeight
                  ? this.scrollBy(0, this.layout.height, !0)
                  : (t = this.views.last().section.next()));
            } else t = this.views.last().section.next();
          else
            ((this.scrollLeft = this.container.scrollLeft),
              this.container.scrollLeft +
                this.container.offsetWidth +
                this.layout.delta <=
              this.container.scrollWidth
                ? this.scrollBy(this.layout.delta, 0, !0)
                : (t = this.views.last().section.next()));
          if (t) {
            this.clear();
            let e = !1;
            return (
              "pre-paginated" === this.layout.name &&
                2 === this.layout.divisor &&
                t.properties.includes("page-spread-right") &&
                (e = !0),
              this.append(t, e)
                .then(
                  function () {
                    return this.handleNextPrePaginated(e, t, this.append);
                  }.bind(this),
                  (t) => t,
                )
                .then(
                  function () {
                    (this.isPaginated ||
                      "horizontal" !== this.settings.axis ||
                      "rtl" !== this.settings.direction ||
                      "default" !== this.settings.rtlScrollType ||
                      this.scrollTo(this.container.scrollWidth, 0, !0),
                      this.views.show());
                  }.bind(this),
                )
            );
          }
        }
      }
      prev() {
        var t;
        let e = this.settings.direction;
        if (this.views.length) {
          if (
            !this.isPaginated ||
            "horizontal" !== this.settings.axis ||
            (e && "ltr" !== e)
          )
            if (
              this.isPaginated &&
              "horizontal" === this.settings.axis &&
              "rtl" === e
            )
              ((this.scrollLeft = this.container.scrollLeft),
                "default" === this.settings.rtlScrollType
                  ? this.container.scrollLeft + this.container.offsetWidth <
                    this.container.scrollWidth
                    ? this.scrollBy(-this.layout.delta, 0, !0)
                    : (t = this.views.first().section.prev())
                  : this.container.scrollLeft < 0
                    ? this.scrollBy(-this.layout.delta, 0, !0)
                    : (t = this.views.first().section.prev()));
            else if (this.isPaginated && "vertical" === this.settings.axis) {
              ((this.scrollTop = this.container.scrollTop),
                this.container.scrollTop > 0
                  ? this.scrollBy(0, -this.layout.height, !0)
                  : (t = this.views.first().section.prev()));
            } else t = this.views.first().section.prev();
          else
            ((this.scrollLeft = this.container.scrollLeft),
              this.container.scrollLeft > 0
                ? this.scrollBy(-this.layout.delta, 0, !0)
                : (t = this.views.first().section.prev()));
          if (t) {
            this.clear();
            let e = !1;
            return (
              "pre-paginated" === this.layout.name &&
                2 === this.layout.divisor &&
                "object" != typeof t.prev() &&
                (e = !0),
              this.prepend(t, e)
                .then(
                  function () {
                    var e;
                    if (
                      "pre-paginated" === this.layout.name &&
                      this.layout.divisor > 1 &&
                      (e = t.prev())
                    )
                      return this.prepend(e);
                  }.bind(this),
                  (t) => t,
                )
                .then(
                  function () {
                    (this.isPaginated &&
                      "horizontal" === this.settings.axis &&
                      ("rtl" === this.settings.direction
                        ? "default" === this.settings.rtlScrollType
                          ? this.scrollTo(0, 0, !0)
                          : this.scrollTo(
                              -1 * this.container.scrollWidth +
                                this.layout.delta,
                              0,
                              !0,
                            )
                        : this.scrollTo(
                            this.container.scrollWidth - this.layout.delta,
                            0,
                            !0,
                          )),
                      this.views.show());
                  }.bind(this),
                )
            );
          }
        }
      }
      current() {
        var t = this.visible();
        return t.length ? t[t.length - 1] : null;
      }
      clear() {
        this.views &&
          (this.views.hide(), this.scrollTo(0, 0, !0), this.views.clear());
      }
      currentLocation() {
        return (
          this.isPaginated && "horizontal" === this.settings.axis
            ? (this.location = this.paginatedLocation())
            : (this.location = this.scrolledLocation()),
          this.location
        );
      }
      scrolledLocation() {
        let t = this.visible(),
          e = this.container.getBoundingClientRect(),
          n = e.height < window.innerHeight ? e.height : window.innerHeight,
          i = e.width < window.innerWidth ? e.width : window.innerWidth,
          r = "vertical" === this.settings.axis,
          s = (this.settings.direction, 0);
        return (
          this.settings.fullsize && (s = r ? window.scrollY : window.scrollX),
          t.map((t) => {
            let o,
              a,
              h,
              l,
              { index: u, href: c } = t.section,
              d = t.position(),
              f = t.width(),
              p = t.height();
            r
              ? ((o = s + e.top - d.top + 0),
                (a = o + n - 0),
                (l = this.layout.count(p, n).pages),
                (h = n))
              : ((o = s + e.left - d.left + 0),
                (a = o + i - 0),
                (l = this.layout.count(f, i).pages),
                (h = i));
            let g = Math.ceil(o / h),
              m = [],
              v = Math.ceil(a / h);
            if ("rtl" === this.settings.direction && !r) {
              let t = g;
              ((g = l - v), (v = l - t));
            }
            m = [];
            for (var y = g; y <= v; y++) {
              let t = y + 1;
              m.push(t);
            }
            return {
              index: u,
              href: c,
              pages: m,
              totalPages: l,
              mapping: this.mapping.page(t.contents, t.section.cfiBase, o, a),
            };
          })
        );
      }
      paginatedLocation() {
        let t = this.visible(),
          e = this.container.getBoundingClientRect(),
          n = 0,
          i = 0;
        return (
          this.settings.fullsize && (n = window.scrollX),
          t.map((t) => {
            let r,
              s,
              o,
              a,
              { index: h, href: l } = t.section,
              u = t.position(),
              c = t.width();
            ("rtl" === this.settings.direction
              ? ((r = e.right - n),
                (a = Math.min(Math.abs(r - u.left), this.layout.width) - i),
                (o = u.width - (u.right - r) - i),
                (s = o - a))
              : ((r = e.left + n),
                (a = Math.min(u.right - r, this.layout.width) - i),
                (s = r - u.left + i),
                (o = s + a)),
              (i += a));
            let d = this.mapping.page(t.contents, t.section.cfiBase, s, o),
              f = this.layout.count(c).pages,
              p = Math.floor(s / this.layout.pageWidth),
              g = [],
              m = Math.floor(o / this.layout.pageWidth);
            if (
              (p < 0 && ((p = 0), (m += 1)), "rtl" === this.settings.direction)
            ) {
              let t = p;
              ((p = f - m), (m = f - t));
            }
            for (var v = p + 1; v <= m; v++) {
              let t = v;
              g.push(t);
            }
            return {
              index: h,
              href: l,
              pages: g,
              totalPages: f,
              mapping: d,
            };
          })
        );
      }
      isVisible(t, e, n, i) {
        var r = t.position(),
          s = i || this.bounds();
        return (
          ("horizontal" === this.settings.axis &&
            r.right > s.left - e &&
            r.left < s.right + n) ||
          ("vertical" === this.settings.axis &&
            r.bottom > s.top - e &&
            r.top < s.bottom + n)
        );
      }
      visible() {
        for (
          var t,
            e = this.bounds(),
            n = this.views.displayed(),
            i = n.length,
            r = [],
            s = 0;
          s < i;
          s++
        )
          ((t = n[s]), !0 === this.isVisible(t, 0, 0, e) && r.push(t));
        return r;
      }
      scrollBy(t, e, n) {
        let i = "rtl" === this.settings.direction ? -1 : 1;
        (n && (this.ignore = !0),
          this.settings.fullsize
            ? window.scrollBy(t * i, e * i)
            : (t && (this.container.scrollLeft += t * i),
              e && (this.container.scrollTop += e)),
          (this.scrolled = !0));
      }
      scrollTo(t, e, n) {
        (n && (this.ignore = !0),
          this.settings.fullsize
            ? window.scrollTo(t, e)
            : ((this.container.scrollLeft = t), (this.container.scrollTop = e)),
          (this.scrolled = !0));
      }
      onScroll() {
        let t, e;
        (this.settings.fullsize
          ? ((t = window.scrollY), (e = window.scrollX))
          : ((t = this.container.scrollTop), (e = this.container.scrollLeft)),
          (this.scrollTop = t),
          (this.scrollLeft = e),
          this.ignore
            ? (this.ignore = !1)
            : (this.emit(f.c.MANAGERS.SCROLL, {
                top: t,
                left: e,
              }),
              clearTimeout(this.afterScrolled),
              (this.afterScrolled = setTimeout(
                function () {
                  this.emit(f.c.MANAGERS.SCROLLED, {
                    top: this.scrollTop,
                    left: this.scrollLeft,
                  });
                }.bind(this),
                20,
              ))));
      }
      bounds() {
        return this.stage.bounds();
      }
      applyLayout(t) {
        ((this.layout = t),
          this.updateLayout(),
          this.views &&
            this.views.length > 0 &&
            "pre-paginated" === this.layout.name &&
            this.display(this.views.first().section));
      }
      updateLayout() {
        this.stage &&
          ((this._stageSize = this.stage.size()),
          this.isPaginated
            ? (this.layout.calculate(
                this._stageSize.width,
                this._stageSize.height,
                this.settings.gap,
              ),
              (this.settings.offset = this.layout.delta / this.layout.divisor))
            : this.layout.calculate(
                this._stageSize.width,
                this._stageSize.height,
              ),
          (this.viewSettings.width = this.layout.width),
          (this.viewSettings.height = this.layout.height),
          this.setLayout(this.layout));
      }
      setLayout(t) {
        ((this.viewSettings.layout = t),
          (this.mapping = new a.a(
            t.props,
            this.settings.direction,
            this.settings.axis,
          )),
          this.views &&
            this.views.forEach(function (e) {
              e && e.setLayout(t);
            }));
      }
      updateWritingMode(t) {
        this.writingMode = t;
      }
      updateAxis(t, e) {
        (e || t !== this.settings.axis) &&
          ((this.settings.axis = t),
          this.stage && this.stage.axis(t),
          (this.viewSettings.axis = t),
          this.mapping &&
            (this.mapping = new a.a(
              this.layout.props,
              this.settings.direction,
              this.settings.axis,
            )),
          this.layout &&
            ("vertical" === t
              ? this.layout.spread("none")
              : this.layout.spread(this.layout.settings.spread)));
      }
      updateFlow(t, e = "auto") {
        let n = "paginated" === t || "auto" === t;
        ((this.isPaginated = n),
          "scrolled-doc" === t ||
          "scrolled-continuous" === t ||
          "scrolled" === t
            ? this.updateAxis("vertical")
            : this.updateAxis("horizontal"),
          (this.viewSettings.flow = t),
          this.settings.overflow
            ? (this.overflow = this.settings.overflow)
            : (this.overflow = n ? "hidden" : e),
          this.stage && this.stage.overflow(this.overflow),
          this.updateLayout());
      }
      getContents() {
        var t = [];
        return this.views
          ? (this.views.forEach(function (e) {
              const n = e && e.contents;
              n && t.push(n);
            }),
            t)
          : t;
      }
      direction(t = "ltr") {
        ((this.settings.direction = t),
          this.stage && this.stage.direction(t),
          (this.viewSettings.direction = t),
          this.updateLayout());
      }
      isRendered() {
        return this.rendered;
      }
    }
    r()(p.prototype);
    e.a = p;
  },
  14: function (t, e, n) {
    "use strict";
    var i = n(2),
      r = n(0);
    e.a = class {
      constructor(t, e, n, i = !1) {
        ((this.layout = t),
          (this.horizontal = "horizontal" === n),
          (this.direction = e || "ltr"),
          (this._dev = i));
      }
      section(t) {
        var e = this.findRanges(t);
        return this.rangeListToCfiList(t.section.cfiBase, e);
      }
      page(t, e, n, r) {
        var s,
          o = !(!t || !t.document) && t.document.body;
        if (o) {
          if (
            ((s = this.rangePairToCfiPair(e, {
              start: this.findStart(o, n, r),
              end: this.findEnd(o, n, r),
            })),
            !0 === this._dev)
          ) {
            let e = t.document,
              n = new i.a(s.start).toRange(e),
              r = new i.a(s.end).toRange(e),
              o = e.defaultView.getSelection(),
              a = e.createRange();
            (o.removeAllRanges(),
              a.setStart(n.startContainer, n.startOffset),
              a.setEnd(r.endContainer, r.endOffset),
              o.addRange(a));
          }
          return s;
        }
      }
      walk(t, e) {
        if (!t || t.nodeType !== Node.TEXT_NODE) {
          var n = function (t) {
              return t.data.trim().length > 0
                ? NodeFilter.FILTER_ACCEPT
                : NodeFilter.FILTER_REJECT;
            },
            i = n;
          i.acceptNode = n;
          for (
            var r,
              s,
              o = document.createTreeWalker(t, NodeFilter.SHOW_TEXT, i, !1);
            (r = o.nextNode()) && !(s = e(r));
          );
          return s;
        }
      }
      findRanges(t) {
        for (
          var e,
            n,
            i = [],
            r = t.contents.scrollWidth(),
            s = Math.ceil(r / this.layout.spreadWidth) * this.layout.divisor,
            o = this.layout.columnWidth,
            a = this.layout.gap,
            h = 0;
          h < s.pages;
          h++
        )
          ((e = (o + a) * h),
            (n = o * (h + 1) + a * h),
            i.push({
              start: this.findStart(t.document.body, e, n),
              end: this.findEnd(t.document.body, e, n),
            }));
        return i;
      }
      findStart(t, e, n) {
        for (var i, s, o = [t], a = t; o.length; )
          if (
            ((i = o.shift()),
            (s = this.walk(i, (t) => {
              var i, s, h, l, u;
              if (
                ((u = Object(r.nodeBounds)(t)),
                this.horizontal && "ltr" === this.direction)
              ) {
                if (
                  ((i = this.horizontal ? u.left : u.top),
                  (s = this.horizontal ? u.right : u.bottom),
                  i >= e && i <= n)
                )
                  return t;
                if (s > e) return t;
                ((a = t), o.push(t));
              } else if (this.horizontal && "rtl" === this.direction) {
                if (((i = u.left), (s = u.right) <= n && s >= e)) return t;
                if (i < n) return t;
                ((a = t), o.push(t));
              } else {
                if (((h = u.top), (l = u.bottom), h >= e && h <= n)) return t;
                if (l > e) return t;
                ((a = t), o.push(t));
              }
            })))
          )
            return this.findTextStartRange(s, e, n);
        return this.findTextStartRange(a, e, n);
      }
      findEnd(t, e, n) {
        for (var i, s, o = [t], a = t; o.length; )
          if (
            ((i = o.shift()),
            (s = this.walk(i, (t) => {
              var i, s, h, l, u;
              if (
                ((u = Object(r.nodeBounds)(t)),
                this.horizontal && "ltr" === this.direction)
              ) {
                if (
                  ((i = Math.round(u.left)),
                  (s = Math.round(u.right)),
                  i > n && a)
                )
                  return a;
                if (s > n) return t;
                ((a = t), o.push(t));
              } else if (this.horizontal && "rtl" === this.direction) {
                if (
                  ((i = Math.round(this.horizontal ? u.left : u.top)),
                  (s = Math.round(this.horizontal ? u.right : u.bottom)) < e &&
                    a)
                )
                  return a;
                if (i < e) return t;
                ((a = t), o.push(t));
              } else {
                if (
                  ((h = Math.round(u.top)),
                  (l = Math.round(u.bottom)),
                  h > n && a)
                )
                  return a;
                if (l > n) return t;
                ((a = t), o.push(t));
              }
            })))
          )
            return this.findTextEndRange(s, e, n);
        return this.findTextEndRange(a, e, n);
      }
      findTextStartRange(t, e, n) {
        for (
          var i, r, s = this.splitTextNodeIntoRanges(t), o = 0;
          o < s.length;
          o++
        )
          if (
            ((r = (i = s[o]).getBoundingClientRect()),
            this.horizontal && "ltr" === this.direction)
          ) {
            if (r.left >= e) return i;
          } else if (this.horizontal && "rtl" === this.direction) {
            if (r.right <= n) return i;
          } else if (r.top >= e) return i;
        return s[0];
      }
      findTextEndRange(t, e, n) {
        for (
          var i, r, s, o, a, h, l, u = this.splitTextNodeIntoRanges(t), c = 0;
          c < u.length;
          c++
        ) {
          if (
            ((s = (r = u[c]).getBoundingClientRect()),
            this.horizontal && "ltr" === this.direction)
          ) {
            if (((o = s.left), (a = s.right), o > n && i)) return i;
            if (a > n) return r;
          } else if (this.horizontal && "rtl" === this.direction) {
            if (((o = s.left), (a = s.right) < e && i)) return i;
            if (o < e) return r;
          } else {
            if (((h = s.top), (l = s.bottom), h > n && i)) return i;
            if (l > n) return r;
          }
          i = r;
        }
        return u[u.length - 1];
      }
      splitTextNodeIntoRanges(t, e) {
        var n,
          i = [],
          r = (t.textContent || "").trim(),
          s = t.ownerDocument,
          o = e || " ",
          a = r.indexOf(o);
        if (-1 === a || t.nodeType != Node.TEXT_NODE)
          return ((n = s.createRange()).selectNodeContents(t), [n]);
        for (
          (n = s.createRange()).setStart(t, 0),
            n.setEnd(t, a),
            i.push(n),
            n = !1;
          -1 != a;
        )
          (a = r.indexOf(o, a + 1)) > 0 &&
            (n && (n.setEnd(t, a), i.push(n)),
            (n = s.createRange()).setStart(t, a + 1));
        return (n && (n.setEnd(t, r.length), i.push(n)), i);
      }
      rangePairToCfiPair(t, e) {
        var n = e.start,
          r = e.end;
        return (
          n.collapse(!0),
          r.collapse(!1),
          {
            start: new i.a(n, t).toString(),
            end: new i.a(r, t).toString(),
          }
        );
      }
      rangeListToCfiList(t, e) {
        for (var n, i = [], r = 0; r < e.length; r++)
          ((n = this.rangePairToCfiPair(t, e[r])), i.push(n));
        return i;
      }
      axis(t) {
        return (t && (this.horizontal = "horizontal" === t), this.horizontal);
      }
    };
  },
  15: function (t, e, n) {
    "use strict";
    var i = n(3),
      r = n.n(i),
      s = n(0),
      o = n(5),
      a = n(4),
      h = n(2),
      l = n(6),
      u = n(8);
    var c = function (t, e, n, i) {
        var r,
          o = "undefined" != typeof window && window.URL,
          h = o ? "blob" : "arraybuffer",
          l = new s.defer(),
          u = new XMLHttpRequest(),
          c = XMLHttpRequest.prototype;
        for (r in ("overrideMimeType" in c ||
          Object.defineProperty(c, "overrideMimeType", {
            value: function () {},
          }),
        n && (u.withCredentials = !0),
        (u.onreadystatechange = function () {
          if (this.readyState === XMLHttpRequest.DONE) {
            var t = !1;
            if (
              (("" !== this.responseType && "document" !== this.responseType) ||
                (t = this.responseXML),
              200 === this.status || 0 === this.status || t)
            ) {
              var n;
              if (!this.response && !t)
                return (
                  l.reject({
                    status: this.status,
                    message: "Empty Response",
                    stack: new Error().stack,
                  }),
                  l.promise
                );
              if (403 === this.status)
                return (
                  l.reject({
                    status: this.status,
                    response: this.response,
                    message: "Forbidden",
                    stack: new Error().stack,
                  }),
                  l.promise
                );
              ((n = t
                ? this.responseXML
                : Object(s.isXml)(e)
                  ? Object(s.parse)(this.response, "text/xml")
                  : "xhtml" == e
                    ? Object(s.parse)(this.response, "application/xhtml+xml")
                    : "html" == e || "htm" == e
                      ? Object(s.parse)(this.response, "text/html")
                      : "json" == e
                        ? JSON.parse(this.response)
                        : "blob" == e
                          ? o
                            ? this.response
                            : new Blob([this.response])
                          : this.response),
                l.resolve(n));
            } else
              l.reject({
                status: this.status,
                message: this.response,
                stack: new Error().stack,
              });
          }
        }),
        (u.onerror = function (t) {
          l.reject(t);
        }),
        u.open("GET", t, !0),
        i))
          u.setRequestHeader(r, i[r]);
        return (
          "json" == e && u.setRequestHeader("Accept", "application/json"),
          e || (e = new a.a(t).extension),
          "blob" == e && (u.responseType = h),
          Object(s.isXml)(e) && u.overrideMimeType("text/xml"),
          "binary" == e && (u.responseType = "arraybuffer"),
          u.send(),
          l.promise
        );
      },
      d = n(18);
    var f = class {
      constructor(t, e) {
        ((this.idref = t.idref),
          (this.linear = "yes" === t.linear),
          (this.properties = t.properties),
          (this.index = t.index),
          (this.href = t.href),
          (this.url = t.url),
          (this.canonical = t.canonical),
          (this.next = t.next),
          (this.prev = t.prev),
          (this.cfiBase = t.cfiBase),
          e
            ? (this.hooks = e)
            : ((this.hooks = {}),
              (this.hooks.serialize = new l.a(this)),
              (this.hooks.content = new l.a(this))),
          (this.document = void 0),
          (this.contents = void 0),
          (this.output = void 0));
      }
      load(t) {
        var e = t || this.request || c,
          n = new s.defer(),
          i = n.promise;
        return (
          this.contents
            ? n.resolve(this.contents)
            : e(this.url)
                .then(
                  function (t) {
                    return (
                      (this.document = t),
                      (this.contents = t.documentElement),
                      this.hooks.content.trigger(this.document, this)
                    );
                  }.bind(this),
                )
                .then(
                  function () {
                    n.resolve(this.contents);
                  }.bind(this),
                )
                .catch(function (t) {
                  n.reject(t);
                }),
          i
        );
      }
      base() {
        return Object(u.a)(this.document, this);
      }
      render(t) {
        var e = new s.defer(),
          n = e.promise;
        return (
          this.output,
          this.load(t)
            .then(
              function (t) {
                var e =
                    (
                      ("undefined" != typeof navigator &&
                        navigator.userAgent) ||
                      ""
                    ).indexOf("Trident") >= 0,
                  n = new (
                    "undefined" == typeof XMLSerializer || e
                      ? d.XMLDOMParser
                      : XMLSerializer
                  )();
                return ((this.output = n.serializeToString(t)), this.output);
              }.bind(this),
            )
            .then(
              function () {
                return this.hooks.serialize.trigger(this.output, this);
              }.bind(this),
            )
            .then(
              function () {
                e.resolve(this.output);
              }.bind(this),
            )
            .catch(function (t) {
              e.reject(t);
            }),
          n
        );
      }
      find(t) {
        var e = this,
          n = [],
          i = t.toLowerCase();
        return (
          Object(s.sprint)(e.document, function (t) {
            !(function (t) {
              for (
                var r,
                  s,
                  o,
                  a = t.textContent.toLowerCase(),
                  h = e.document.createRange(),
                  l = -1;
                -1 != s;
              )
                (-1 != (s = a.indexOf(i, l + 1)) &&
                  ((h = e.document.createRange()).setStart(t, s),
                  h.setEnd(t, s + i.length),
                  (r = e.cfiFromRange(h)),
                  (o =
                    t.textContent.length < 150
                      ? t.textContent
                      : "..." +
                        (o = t.textContent.substring(s - 75, s + 75)) +
                        "..."),
                  n.push({
                    cfi: r,
                    excerpt: o,
                  })),
                  (l = s));
            })(t);
          }),
          n
        );
      }
      search(t, e = 5) {
        if (void 0 === document.createTreeWalker) return this.find(t);
        let n = [];
        const i = this,
          r = t.toLowerCase(),
          s = function (t) {
            const e = t
              .reduce((t, e) => t + e.textContent, "")
              .toLowerCase()
              .indexOf(r);
            if (-1 != e) {
              const s = 0,
                o = e + r.length;
              let a = 0,
                h = 0;
              if (e < t[s].length) {
                let r;
                for (; a < t.length - 1 && ((h += t[a].length), !(o <= h)); )
                  a += 1;
                let l = t[s],
                  u = t[a],
                  c = i.document.createRange();
                c.setStart(l, e);
                let d = t
                  .slice(0, a)
                  .reduce((t, e) => t + e.textContent.length, 0);
                (c.setEnd(u, d > o ? o : o - d), (r = i.cfiFromRange(c)));
                let f = t
                  .slice(0, a + 1)
                  .reduce((t, e) => t + e.textContent, "");
                (f.length > 150 &&
                  ((f = f.substring(e - 75, e + 75)), (f = "..." + f + "...")),
                  n.push({
                    cfi: r,
                    excerpt: f,
                  }));
              }
            }
          },
          o = document.createTreeWalker(
            i.document,
            NodeFilter.SHOW_TEXT,
            null,
            !1,
          );
        let a,
          h = [];
        for (; (a = o.nextNode()); )
          (h.push(a), h.length == e && (s(h.slice(0, e)), (h = h.slice(1, e))));
        return (h.length > 0 && s(h), n);
      }
      reconcileLayoutSettings(t) {
        var e = {
          layout: t.layout,
          spread: t.spread,
          orientation: t.orientation,
        };
        return (
          this.properties.forEach(function (t) {
            var n,
              i,
              r = t.replace("rendition:", ""),
              s = r.indexOf("-");
            -1 != s && ((n = r.slice(0, s)), (i = r.slice(s + 1)), (e[n] = i));
          }),
          e
        );
      }
      cfiFromRange(t) {
        return new h.a(t, this.cfiBase).toString();
      }
      cfiFromElement(t) {
        return new h.a(t, this.cfiBase).toString();
      }
      unload() {
        ((this.document = void 0),
          (this.contents = void 0),
          (this.output = void 0));
      }
      destroy() {
        (this.unload(),
          this.hooks.serialize.clear(),
          this.hooks.content.clear(),
          (this.hooks = void 0),
          (this.idref = void 0),
          (this.linear = void 0),
          (this.properties = void 0),
          (this.index = void 0),
          (this.href = void 0),
          (this.url = void 0),
          (this.next = void 0),
          (this.prev = void 0),
          (this.cfiBase = void 0));
      }
    };
    var p = class {
        constructor() {
          ((this.spineItems = []),
            (this.spineByHref = {}),
            (this.spineById = {}),
            (this.hooks = {}),
            (this.hooks.serialize = new l.a()),
            (this.hooks.content = new l.a()),
            this.hooks.content.register(u.a),
            this.hooks.content.register(u.b),
            this.hooks.content.register(u.d),
            (this.epubcfi = new h.a()),
            (this.loaded = !1),
            (this.items = void 0),
            (this.manifest = void 0),
            (this.spineNodeIndex = void 0),
            (this.baseUrl = void 0),
            (this.length = void 0));
        }
        unpack(t, e, n) {
          ((this.items = t.spine),
            (this.manifest = t.manifest),
            (this.spineNodeIndex = t.spineNodeIndex),
            (this.baseUrl = t.baseUrl || t.basePath || ""),
            (this.length = this.items.length),
            this.items.forEach((t, i) => {
              var r,
                s = this.manifest[t.idref];
              ((t.index = i),
                (t.cfiBase = this.epubcfi.generateChapterComponent(
                  this.spineNodeIndex,
                  t.index,
                  t.idref,
                )),
                t.href && ((t.url = e(t.href, !0)), (t.canonical = n(t.href))),
                s &&
                  ((t.href = s.href),
                  (t.url = e(t.href, !0)),
                  (t.canonical = n(t.href)),
                  s.properties.length &&
                    t.properties.push.apply(t.properties, s.properties)),
                "yes" === t.linear
                  ? ((t.prev = function () {
                      let e = t.index;
                      for (; e > 0; ) {
                        let t = this.get(e - 1);
                        if (t && t.linear) return t;
                        e -= 1;
                      }
                    }.bind(this)),
                    (t.next = function () {
                      let e = t.index;
                      for (; e < this.spineItems.length - 1; ) {
                        let t = this.get(e + 1);
                        if (t && t.linear) return t;
                        e += 1;
                      }
                    }.bind(this)))
                  : ((t.prev = function () {}), (t.next = function () {})),
                (r = new f(t, this.hooks)),
                this.append(r));
            }),
            (this.loaded = !0));
        }
        get(t) {
          var e = 0;
          if (void 0 === t)
            for (; e < this.spineItems.length; ) {
              let t = this.spineItems[e];
              if (t && t.linear) break;
              e += 1;
            }
          else if (this.epubcfi.isCfiString(t)) {
            e = new h.a(t).spinePos;
          } else
            "number" == typeof t || !1 === isNaN(t)
              ? (e = t)
              : "string" == typeof t && 0 === t.indexOf("#")
                ? (e = this.spineById[t.substring(1)])
                : "string" == typeof t &&
                  ((t = t.split("#")[0]),
                  (e = this.spineByHref[t] || this.spineByHref[encodeURI(t)]));
          return this.spineItems[e] || null;
        }
        append(t) {
          var e = this.spineItems.length;
          return (
            (t.index = e),
            this.spineItems.push(t),
            (this.spineByHref[decodeURI(t.href)] = e),
            (this.spineByHref[encodeURI(t.href)] = e),
            (this.spineByHref[t.href] = e),
            (this.spineById[t.idref] = e),
            e
          );
        }
        prepend(t) {
          return (
            (this.spineByHref[t.href] = 0),
            (this.spineById[t.idref] = 0),
            this.spineItems.forEach(function (t, e) {
              t.index = e;
            }),
            0
          );
        }
        remove(t) {
          var e = this.spineItems.indexOf(t);
          if (e > -1)
            return (
              delete this.spineByHref[t.href],
              delete this.spineById[t.idref],
              this.spineItems.splice(e, 1)
            );
        }
        each() {
          return this.spineItems.forEach.apply(this.spineItems, arguments);
        }
        first() {
          let t = 0;
          do {
            let e = this.get(t);
            if (e && e.linear) return e;
            t += 1;
          } while (t < this.spineItems.length);
        }
        last() {
          let t = this.spineItems.length - 1;
          do {
            let e = this.get(t);
            if (e && e.linear) return e;
            t -= 1;
          } while (t >= 0);
        }
        destroy() {
          (this.each((t) => t.destroy()),
            (this.spineItems = void 0),
            (this.spineByHref = void 0),
            (this.spineById = void 0),
            this.hooks.serialize.clear(),
            this.hooks.content.clear(),
            (this.hooks = void 0),
            (this.epubcfi = void 0),
            (this.loaded = !1),
            (this.items = void 0),
            (this.manifest = void 0),
            (this.spineNodeIndex = void 0),
            (this.baseUrl = void 0),
            (this.length = void 0));
        }
      },
      g = n(12),
      m = n(1);
    class v {
      constructor(t, e, n) {
        ((this.spine = t),
          (this.request = e),
          (this.pause = n || 100),
          (this.q = new g.a(this)),
          (this.epubcfi = new h.a()),
          (this._locations = []),
          (this._locationsWords = []),
          (this.total = 0),
          (this.break = 150),
          (this._current = 0),
          (this._wordCounter = 0),
          (this.currentLocation = ""),
          (this._currentCfi = ""),
          (this.processingTimeout = void 0));
      }
      generate(t) {
        return (
          t && (this.break = t),
          this.q.pause(),
          this.spine.each(
            function (t) {
              t.linear && this.q.enqueue(this.process.bind(this), t);
            }.bind(this),
          ),
          this.q.run().then(
            function () {
              return (
                (this.total = this._locations.length - 1),
                this._currentCfi && (this.currentLocation = this._currentCfi),
                this._locations
              );
            }.bind(this),
          )
        );
      }
      createRange() {
        return {
          startContainer: void 0,
          startOffset: void 0,
          endContainer: void 0,
          endOffset: void 0,
        };
      }
      process(t) {
        return t.load(this.request).then(
          function (e) {
            var n = new s.defer(),
              i = this.parse(e, t.cfiBase);
            return (
              (this._locations = this._locations.concat(i)),
              t.unload(),
              (this.processingTimeout = setTimeout(
                () => n.resolve(i),
                this.pause,
              )),
              n.promise
            );
          }.bind(this),
        );
      }
      parse(t, e, n) {
        var i,
          r,
          o = [],
          a = t.ownerDocument,
          l = Object(s.qs)(a, "body"),
          u = 0,
          c = n || this.break;
        if (
          (Object(s.sprint)(
            l,
            function (t) {
              var n,
                s = t.length,
                a = 0;
              if (0 === t.textContent.trim().length) return !1;
              for (
                0 == u &&
                  (((i = this.createRange()).startContainer = t),
                  (i.startOffset = 0)),
                  (n = c - u) > s && ((u += s), (a = s));
                a < s;
              )
                if (
                  ((n = c - u),
                  0 === u &&
                    ((a += 1),
                    ((i = this.createRange()).startContainer = t),
                    (i.startOffset = a)),
                  a + n >= s)
                )
                  ((u += s - a), (a = s));
                else {
                  ((a += n), (i.endContainer = t), (i.endOffset = a));
                  let r = new h.a(i, e).toString();
                  (o.push(r), (u = 0));
                }
              r = t;
            }.bind(this),
          ),
          i && i.startContainer && r)
        ) {
          ((i.endContainer = r), (i.endOffset = r.length));
          let t = new h.a(i, e).toString();
          (o.push(t), (u = 0));
        }
        return o;
      }
      generateFromWords(t, e, n) {
        var i = t ? new h.a(t) : void 0;
        return (
          this.q.pause(),
          (this._locationsWords = []),
          (this._wordCounter = 0),
          this.spine.each(
            function (t) {
              t.linear &&
                (i
                  ? t.index >= i.spinePos &&
                    this.q.enqueue(this.processWords.bind(this), t, e, i, n)
                  : this.q.enqueue(this.processWords.bind(this), t, e, i, n));
            }.bind(this),
          ),
          this.q.run().then(
            function () {
              return (
                this._currentCfi && (this.currentLocation = this._currentCfi),
                this._locationsWords
              );
            }.bind(this),
          )
        );
      }
      processWords(t, e, n, i) {
        return i && this._locationsWords.length >= i
          ? Promise.resolve()
          : t.load(this.request).then(
              function (r) {
                var o = new s.defer(),
                  a = this.parseWords(r, t, e, n),
                  h = i - this._locationsWords.length;
                return (
                  (this._locationsWords = this._locationsWords.concat(
                    a.length >= i ? a.slice(0, h) : a,
                  )),
                  t.unload(),
                  (this.processingTimeout = setTimeout(
                    () => o.resolve(a),
                    this.pause,
                  )),
                  o.promise
                );
              }.bind(this),
            );
      }
      countWords(t) {
        return (t = (t = (t = t.replace(/(^\s*)|(\s*$)/gi, "")).replace(
          /[ ]{2,}/gi,
          " ",
        )).replace(/\n /, "\n")).split(" ").length;
      }
      parseWords(t, e, n, i) {
        var r,
          o = e.cfiBase,
          a = [],
          l = t.ownerDocument,
          u = Object(s.qs)(l, "body"),
          c = n,
          d = !i || i.spinePos !== e.index;
        i &&
          e.index === i.spinePos &&
          (r = i.findNode(
            i.range ? i.path.steps.concat(i.start.steps) : i.path.steps,
            t.ownerDocument,
          ));
        return (
          Object(s.sprint)(
            u,
            function (t) {
              if (!d) {
                if (t !== r) return !1;
                d = !0;
              }
              if (
                t.textContent.length < 10 &&
                0 === t.textContent.trim().length
              )
                return !1;
              var e,
                n = this.countWords(t.textContent),
                i = 0;
              if (0 === n) return !1;
              for (
                (e = c - this._wordCounter) > n &&
                ((this._wordCounter += n), (i = n));
                i < n;
              )
                if (i + (e = c - this._wordCounter) >= n)
                  ((this._wordCounter += n - i), (i = n));
                else {
                  i += e;
                  let n = new h.a(t, o);
                  (a.push({
                    cfi: n.toString(),
                    wordCount: this._wordCounter,
                  }),
                    (this._wordCounter = 0));
                }
              t;
            }.bind(this),
          ),
          a
        );
      }
      locationFromCfi(t) {
        let e;
        return (
          h.a.prototype.isCfiString(t) && (t = new h.a(t)),
          0 === this._locations.length
            ? -1
            : ((e = Object(s.locationOf)(
                t,
                this._locations,
                this.epubcfi.compare,
              )),
              e > this.total ? this.total : e)
        );
      }
      percentageFromCfi(t) {
        if (0 === this._locations.length) return null;
        var e = this.locationFromCfi(t);
        return this.percentageFromLocation(e);
      }
      percentageFromLocation(t) {
        return t && this.total ? t / this.total : 0;
      }
      cfiFromLocation(t) {
        var e = -1;
        return (
          "number" != typeof t && (t = parseInt(t)),
          t >= 0 && t < this._locations.length && (e = this._locations[t]),
          e
        );
      }
      cfiFromPercentage(t) {
        let e;
        if (
          (t > 1 &&
            console.warn("Normalize cfiFromPercentage value to between 0 - 1"),
          t >= 1)
        ) {
          let t = new h.a(this._locations[this.total]);
          return (t.collapse(), t.toString());
        }
        return ((e = Math.ceil(this.total * t)), this.cfiFromLocation(e));
      }
      load(t) {
        return (
          (this._locations = "string" == typeof t ? JSON.parse(t) : t),
          (this.total = this._locations.length - 1),
          this._locations
        );
      }
      save() {
        return JSON.stringify(this._locations);
      }
      getCurrent() {
        return this._current;
      }
      setCurrent(t) {
        var e;
        if ("string" == typeof t) this._currentCfi = t;
        else {
          if ("number" != typeof t) return;
          this._current = t;
        }
        0 !== this._locations.length &&
          ("string" == typeof t
            ? ((e = this.locationFromCfi(t)), (this._current = e))
            : (e = t),
          this.emit(m.c.LOCATIONS.CHANGED, {
            percentage: this.percentageFromLocation(e),
          }));
      }
      get currentLocation() {
        return this._current;
      }
      set currentLocation(t) {
        this.setCurrent(t);
      }
      length() {
        return this._locations.length;
      }
      destroy() {
        ((this.spine = void 0),
          (this.request = void 0),
          (this.pause = void 0),
          this.q.stop(),
          (this.q = void 0),
          (this.epubcfi = void 0),
          (this._locations = void 0),
          (this.total = void 0),
          (this.break = void 0),
          (this._current = void 0),
          (this.currentLocation = void 0),
          (this._currentCfi = void 0),
          clearTimeout(this.processingTimeout));
      }
    }
    r()(v.prototype);
    var y = v,
      b = n(7),
      w = n.n(b);
    var x = class {
      constructor(t) {
        ((this.packagePath = ""),
          (this.directory = ""),
          (this.encoding = ""),
          t && this.parse(t));
      }
      parse(t) {
        var e;
        if (!t) throw new Error("Container File Not Found");
        if (!(e = Object(s.qs)(t, "rootfile")))
          throw new Error("No RootFile Found");
        ((this.packagePath = e.getAttribute("full-path")),
          (this.directory = w.a.dirname(this.packagePath)),
          (this.encoding = t.xmlEncoding));
      }
      destroy() {
        ((this.packagePath = void 0),
          (this.directory = void 0),
          (this.encoding = void 0));
      }
    };
    var _ = class {
      constructor(t) {
        ((this.manifest = {}),
          (this.navPath = ""),
          (this.ncxPath = ""),
          (this.coverPath = ""),
          (this.spineNodeIndex = 0),
          (this.spine = []),
          (this.metadata = {}),
          t && this.parse(t));
      }
      parse(t) {
        var e, n, i;
        if (!t) throw new Error("Package File Not Found");
        if (!(e = Object(s.qs)(t, "metadata")))
          throw new Error("No Metadata Found");
        if (!(n = Object(s.qs)(t, "manifest")))
          throw new Error("No Manifest Found");
        if (!(i = Object(s.qs)(t, "spine"))) throw new Error("No Spine Found");
        return (
          (this.manifest = this.parseManifest(n)),
          (this.navPath = this.findNavPath(n)),
          (this.ncxPath = this.findNcxPath(n, i)),
          (this.coverPath = this.findCoverPath(t)),
          (this.spineNodeIndex = Object(s.indexOfElementNode)(i)),
          (this.spine = this.parseSpine(i, this.manifest)),
          (this.uniqueIdentifier = this.findUniqueIdentifier(t)),
          (this.metadata = this.parseMetadata(e)),
          (this.metadata.direction = i.getAttribute(
            "page-progression-direction",
          )),
          {
            metadata: this.metadata,
            spine: this.spine,
            manifest: this.manifest,
            navPath: this.navPath,
            ncxPath: this.ncxPath,
            coverPath: this.coverPath,
            spineNodeIndex: this.spineNodeIndex,
          }
        );
      }
      parseMetadata(t) {
        var e = {};
        return (
          (e.title = this.getElementText(t, "title")),
          (e.creator = this.getElementText(t, "creator")),
          (e.description = this.getElementText(t, "description")),
          (e.pubdate = this.getElementText(t, "date")),
          (e.publisher = this.getElementText(t, "publisher")),
          (e.identifier = this.getElementText(t, "identifier")),
          (e.language = this.getElementText(t, "language")),
          (e.rights = this.getElementText(t, "rights")),
          (e.modified_date = this.getPropertyText(t, "dcterms:modified")),
          (e.layout = this.getPropertyText(t, "rendition:layout")),
          (e.orientation = this.getPropertyText(t, "rendition:orientation")),
          (e.flow = this.getPropertyText(t, "rendition:flow")),
          (e.viewport = this.getPropertyText(t, "rendition:viewport")),
          (e.media_active_class = this.getPropertyText(
            t,
            "media:active-class",
          )),
          (e.spread = this.getPropertyText(t, "rendition:spread")),
          e
        );
      }
      parseManifest(t) {
        var e = {},
          n = Object(s.qsa)(t, "item");
        return (
          Array.prototype.slice.call(n).forEach(function (t) {
            var n = t.getAttribute("id"),
              i = t.getAttribute("href") || "",
              r = t.getAttribute("media-type") || "",
              s = t.getAttribute("media-overlay") || "",
              o = t.getAttribute("properties") || "";
            e[n] = {
              href: i,
              type: r,
              overlay: s,
              properties: o.length ? o.split(" ") : [],
            };
          }),
          e
        );
      }
      parseSpine(t, e) {
        var n = [],
          i = Object(s.qsa)(t, "itemref");
        return (
          Array.prototype.slice.call(i).forEach(function (t, e) {
            var i = t.getAttribute("idref"),
              r = t.getAttribute("properties") || "",
              s = r.length ? r.split(" ") : [],
              o = {
                idref: i,
                linear: t.getAttribute("linear") || "yes",
                properties: s,
                index: e,
              };
            n.push(o);
          }),
          n
        );
      }
      findUniqueIdentifier(t) {
        var e = t.documentElement.getAttribute("unique-identifier");
        if (!e) return "";
        var n = t.getElementById(e);
        return n &&
          "identifier" === n.localName &&
          "http://purl.org/dc/elements/1.1/" === n.namespaceURI &&
          n.childNodes.length > 0
          ? n.childNodes[0].nodeValue.trim()
          : "";
      }
      findNavPath(t) {
        var e = Object(s.qsp)(t, "item", {
          properties: "nav",
        });
        return !!e && e.getAttribute("href");
      }
      findNcxPath(t, e) {
        var n,
          i = Object(s.qsp)(t, "item", {
            "media-type": "application/x-dtbncx+xml",
          });
        return (
          i || ((n = e.getAttribute("toc")) && (i = t.querySelector("#" + n))),
          !!i && i.getAttribute("href")
        );
      }
      findCoverPath(t) {
        Object(s.qs)(t, "package").getAttribute("version");
        var e = Object(s.qsp)(t, "item", {
          properties: "cover-image",
        });
        if (e) return e.getAttribute("href");
        var n = Object(s.qsp)(t, "meta", {
          name: "cover",
        });
        if (n) {
          var i = n.getAttribute("content"),
            r = t.getElementById(i);
          return r ? r.getAttribute("href") : "";
        }
        return !1;
      }
      getElementText(t, e) {
        var n,
          i = t.getElementsByTagNameNS("http://purl.org/dc/elements/1.1/", e);
        return i && 0 !== i.length && (n = i[0]).childNodes.length
          ? n.childNodes[0].nodeValue
          : "";
      }
      getPropertyText(t, e) {
        var n = Object(s.qsp)(t, "meta", {
          property: e,
        });
        return n && n.childNodes.length ? n.childNodes[0].nodeValue : "";
      }
      load(t) {
        this.metadata = t.metadata;
        let e = t.readingOrder || t.spine;
        return (
          (this.spine = e.map(
            (t, e) => ((t.index = e), (t.linear = t.linear || "yes"), t),
          )),
          t.resources.forEach((t, e) => {
            ((this.manifest[e] = t),
              t.rel && "cover" === t.rel[0] && (this.coverPath = t.href));
          }),
          (this.spineNodeIndex = 0),
          (this.toc = t.toc.map((t, e) => ((t.label = t.title), t))),
          {
            metadata: this.metadata,
            spine: this.spine,
            manifest: this.manifest,
            navPath: this.navPath,
            ncxPath: this.ncxPath,
            coverPath: this.coverPath,
            spineNodeIndex: this.spineNodeIndex,
            toc: this.toc,
          }
        );
      }
      destroy() {
        ((this.manifest = void 0),
          (this.navPath = void 0),
          (this.ncxPath = void 0),
          (this.coverPath = void 0),
          (this.spineNodeIndex = void 0),
          (this.spine = void 0),
          (this.metadata = void 0));
      }
    };
    var E = class {
        constructor(t) {
          ((this.toc = []),
            (this.tocByHref = {}),
            (this.tocById = {}),
            (this.landmarks = []),
            (this.landmarksByType = {}),
            (this.length = 0),
            t && this.parse(t));
        }
        parse(t) {
          let e,
            n,
            i = t.nodeType;
          (i && ((e = Object(s.qs)(t, "html")), (n = Object(s.qs)(t, "ncx"))),
            i
              ? e
                ? ((this.toc = this.parseNav(t)),
                  (this.landmarks = this.parseLandmarks(t)))
                : n && (this.toc = this.parseNcx(t))
              : (this.toc = this.load(t)),
            (this.length = 0),
            this.unpack(this.toc));
        }
        unpack(t) {
          for (var e, n = 0; n < t.length; n++)
            ((e = t[n]).href && (this.tocByHref[e.href] = n),
              e.id && (this.tocById[e.id] = n),
              this.length++,
              e.subitems.length && this.unpack(e.subitems));
        }
        get(t) {
          var e;
          return t
            ? (0 === t.indexOf("#")
                ? (e = this.tocById[t.substring(1)])
                : t in this.tocByHref && (e = this.tocByHref[t]),
              this.getByIndex(t, e, this.toc))
            : this.toc;
        }
        getByIndex(t, e, n) {
          if (0 === n.length) return;
          const i = n[e];
          if (!i || (t !== i.id && t !== i.href)) {
            let i;
            for (
              let r = 0;
              r < n.length && ((i = this.getByIndex(t, e, n[r].subitems)), !i);
              ++r
            );
            return i;
          }
          return i;
        }
        landmark(t) {
          var e;
          return t
            ? ((e = this.landmarksByType[t]), this.landmarks[e])
            : this.landmarks;
        }
        parseNav(t) {
          var e,
            n,
            i = Object(s.querySelectorByType)(t, "nav", "toc"),
            r = i ? Object(s.qsa)(i, "li") : [],
            o = r.length,
            a = {},
            h = [];
          if (!r || 0 === o) return h;
          for (e = 0; e < o; ++e)
            (n = this.navItem(r[e])) &&
              ((a[n.id] = n),
              n.parent ? a[n.parent].subitems.push(n) : h.push(n));
          return h;
        }
        navItem(t) {
          let e = t.getAttribute("id") || void 0,
            n = Object(s.filterChildren)(t, "a", !0);
          if (!n) return;
          let i = n.getAttribute("href") || "";
          e || (e = i);
          let r,
            o = n.textContent || "",
            a = Object(s.getParentByTagName)(t, "li");
          if (a && ((r = a.getAttribute("id")), !r)) {
            const t = Object(s.filterChildren)(a, "a", !0);
            r = t && t.getAttribute("href");
          }
          for (; !r && a; )
            if (
              ((a = Object(s.getParentByTagName)(a, "li")),
              a && ((r = a.getAttribute("id")), !r))
            ) {
              const t = Object(s.filterChildren)(a, "a", !0);
              r = t && t.getAttribute("href");
            }
          return {
            id: e,
            href: i,
            label: o,
            subitems: [],
            parent: r,
          };
        }
        parseLandmarks(t) {
          var e,
            n,
            i = Object(s.querySelectorByType)(t, "nav", "landmarks"),
            r = i ? Object(s.qsa)(i, "li") : [],
            o = r.length,
            a = [];
          if (!r || 0 === o) return a;
          for (e = 0; e < o; ++e)
            (n = this.landmarkItem(r[e])) &&
              (a.push(n), (this.landmarksByType[n.type] = e));
          return a;
        }
        landmarkItem(t) {
          let e = Object(s.filterChildren)(t, "a", !0);
          if (!e) return;
          let n =
            e.getAttributeNS("http://www.idpf.org/2007/ops", "type") || void 0;
          return {
            href: e.getAttribute("href") || "",
            label: e.textContent || "",
            type: n,
          };
        }
        parseNcx(t) {
          var e,
            n,
            i = Object(s.qsa)(t, "navPoint"),
            r = i.length,
            o = {},
            a = [];
          if (!i || 0 === r) return a;
          for (e = 0; e < r; ++e)
            ((o[(n = this.ncxItem(i[e])).id] = n),
              n.parent ? o[n.parent].subitems.push(n) : a.push(n));
          return a;
        }
        ncxItem(t) {
          var e,
            n = t.getAttribute("id") || !1,
            i = Object(s.qs)(t, "content").getAttribute("src"),
            r = Object(s.qs)(t, "navLabel"),
            o = r.textContent ? r.textContent : "",
            a = t.parentNode;
          return (
            !a ||
              ("navPoint" !== a.nodeName &&
                "navPoint" !== a.nodeName.split(":").slice(-1)[0]) ||
              (e = a.getAttribute("id")),
            {
              id: n,
              href: i,
              label: o,
              subitems: [],
              parent: e,
            }
          );
        }
        load(t) {
          return t.map(
            (t) => (
              (t.label = t.title),
              (t.subitems = t.children ? this.load(t.children) : []),
              t
            ),
          );
        }
        forEach(t) {
          return this.toc.forEach(t);
        }
      },
      k = {
        application: {
          ecmascript: ["es", "ecma"],
          javascript: "js",
          ogg: "ogx",
          pdf: "pdf",
          postscript: ["ps", "ai", "eps", "epsi", "epsf", "eps2", "eps3"],
          "rdf+xml": "rdf",
          smil: ["smi", "smil"],
          "xhtml+xml": ["xhtml", "xht"],
          xml: ["xml", "xsl", "xsd", "opf", "ncx"],
          zip: "zip",
          "x-httpd-eruby": "rhtml",
          "x-latex": "latex",
          "x-maker": ["frm", "maker", "frame", "fm", "fb", "book", "fbdoc"],
          "x-object": "o",
          "x-shockwave-flash": ["swf", "swfl"],
          "x-silverlight": "scr",
          "epub+zip": "epub",
          "font-tdpfr": "pfr",
          "inkml+xml": ["ink", "inkml"],
          json: "json",
          "jsonml+json": "jsonml",
          "mathml+xml": "mathml",
          "metalink+xml": "metalink",
          mp4: "mp4s",
          "omdoc+xml": "omdoc",
          oxps: "oxps",
          "vnd.amazon.ebook": "azw",
          widget: "wgt",
          "x-dtbook+xml": "dtb",
          "x-dtbresource+xml": "res",
          "x-font-bdf": "bdf",
          "x-font-ghostscript": "gsf",
          "x-font-linux-psf": "psf",
          "x-font-otf": "otf",
          "x-font-pcf": "pcf",
          "x-font-snf": "snf",
          "x-font-ttf": ["ttf", "ttc"],
          "x-font-type1": ["pfa", "pfb", "pfm", "afm"],
          "x-font-woff": "woff",
          "x-mobipocket-ebook": ["prc", "mobi"],
          "x-mspublisher": "pub",
          "x-nzb": "nzb",
          "x-tgif": "obj",
          "xaml+xml": "xaml",
          "xml-dtd": "dtd",
          "xproc+xml": "xpl",
          "xslt+xml": "xslt",
          "internet-property-stream": "acx",
          "x-compress": "z",
          "x-compressed": "tgz",
          "x-gzip": "gz",
        },
        audio: {
          flac: "flac",
          midi: ["mid", "midi", "kar", "rmi"],
          mpeg: ["mpga", "mpega", "mp2", "mp3", "m4a", "mp2a", "m2a", "m3a"],
          mpegurl: "m3u",
          ogg: ["oga", "ogg", "spx"],
          "x-aiff": ["aif", "aiff", "aifc"],
          "x-ms-wma": "wma",
          "x-wav": "wav",
          adpcm: "adp",
          mp4: "mp4a",
          webm: "weba",
          "x-aac": "aac",
          "x-caf": "caf",
          "x-matroska": "mka",
          "x-pn-realaudio-plugin": "rmp",
          xm: "xm",
          mid: ["mid", "rmi"],
        },
        image: {
          gif: "gif",
          ief: "ief",
          jpeg: ["jpeg", "jpg", "jpe"],
          pcx: "pcx",
          png: "png",
          "svg+xml": ["svg", "svgz"],
          tiff: ["tiff", "tif"],
          "x-icon": "ico",
          bmp: "bmp",
          webp: "webp",
          "x-pict": ["pic", "pct"],
          "x-tga": "tga",
          "cis-cod": "cod",
        },
        text: {
          "cache-manifest": ["manifest", "appcache"],
          css: "css",
          csv: "csv",
          html: ["html", "htm", "shtml", "stm"],
          mathml: "mml",
          plain: [
            "txt",
            "text",
            "brf",
            "conf",
            "def",
            "list",
            "log",
            "in",
            "bas",
          ],
          richtext: "rtx",
          "tab-separated-values": "tsv",
          "x-bibtex": "bib",
        },
        video: {
          mpeg: ["mpeg", "mpg", "mpe", "m1v", "m2v", "mp2", "mpa", "mpv2"],
          mp4: ["mp4", "mp4v", "mpg4"],
          quicktime: ["qt", "mov"],
          ogg: "ogv",
          "vnd.mpegurl": ["mxu", "m4u"],
          "x-flv": "flv",
          "x-la-asf": ["lsf", "lsx"],
          "x-mng": "mng",
          "x-ms-asf": ["asf", "asx", "asr"],
          "x-ms-wm": "wm",
          "x-ms-wmv": "wmv",
          "x-ms-wmx": "wmx",
          "x-ms-wvx": "wvx",
          "x-msvideo": "avi",
          "x-sgi-movie": "movie",
          "x-matroska": ["mpv", "mkv", "mk3d", "mks"],
          "3gpp2": "3g2",
          h261: "h261",
          h263: "h263",
          h264: "h264",
          jpeg: "jpgv",
          jpm: ["jpm", "jpgm"],
          mj2: ["mj2", "mjp2"],
          "vnd.ms-playready.media.pyv": "pyv",
          "vnd.uvvu.mp4": ["uvu", "uvvu"],
          "vnd.vivo": "viv",
          webm: "webm",
          "x-f4v": "f4v",
          "x-m4v": "m4v",
          "x-ms-vob": "vob",
          "x-smv": "smv",
        },
      },
      S = (function () {
        var t,
          e,
          n,
          i,
          r = {};
        for (t in k)
          if (k.hasOwnProperty(t))
            for (e in k[t])
              if (k[t].hasOwnProperty(e))
                if ("string" == typeof (n = k[t][e])) r[n] = t + "/" + e;
                else for (i = 0; i < n.length; i++) r[n[i]] = t + "/" + e;
        return r;
      })();
    var C = {
      lookup: function (t) {
        return (t && S[t.split(".").pop().toLowerCase()]) || "text/plain";
      },
    };
    var T = class {
      constructor(t, e) {
        ((this.settings = {
          replacements: (e && e.replacements) || "base64",
          archive: e && e.archive,
          resolver: e && e.resolver,
          request: e && e.request,
        }),
          this.process(t));
      }
      process(t) {
        ((this.manifest = t),
          (this.resources = Object.keys(t).map(function (e) {
            return t[e];
          })),
          (this.replacementUrls = []),
          (this.html = []),
          (this.assets = []),
          (this.css = []),
          (this.urls = []),
          (this.cssUrls = []),
          this.split(),
          this.splitUrls());
      }
      split() {
        ((this.html = this.resources.filter(function (t) {
          if ("application/xhtml+xml" === t.type || "text/html" === t.type)
            return !0;
        })),
          (this.assets = this.resources.filter(function (t) {
            if ("application/xhtml+xml" !== t.type && "text/html" !== t.type)
              return !0;
          })),
          (this.css = this.resources.filter(function (t) {
            if ("text/css" === t.type) return !0;
          })));
      }
      splitUrls() {
        ((this.urls = this.assets.map(
          function (t) {
            return t.href;
          }.bind(this),
        )),
          (this.cssUrls = this.css.map(function (t) {
            return t.href;
          })));
      }
      createUrl(t) {
        var e = new o.a(t),
          n = C.lookup(e.filename);
        return this.settings.archive
          ? this.settings.archive.createUrl(t, {
              base64: "base64" === this.settings.replacements,
            })
          : "base64" === this.settings.replacements
            ? this.settings
                .request(t, "blob")
                .then((t) => Object(s.blob2base64)(t))
                .then((t) => Object(s.createBase64Url)(t, n))
            : this.settings
                .request(t, "blob")
                .then((t) => Object(s.createBlobUrl)(t, n));
      }
      replacements() {
        if ("none" === this.settings.replacements)
          return new Promise(
            function (t) {
              t(this.urls);
            }.bind(this),
          );
        var t = this.urls.map((t) => {
          var e = this.settings.resolver(t);
          return this.createUrl(e).catch((t) => (console.error(t), null));
        });
        return Promise.all(t).then(
          (t) => (
            (this.replacementUrls = t.filter((t) => "string" == typeof t)),
            t
          ),
        );
      }
      replaceCss(t, e) {
        var n = [];
        return (
          (t = t || this.settings.archive),
          (e = e || this.settings.resolver),
          this.cssUrls.forEach(
            function (i) {
              var r = this.createCssFile(i, t, e).then(
                function (t) {
                  var e = this.urls.indexOf(i);
                  e > -1 && (this.replacementUrls[e] = t);
                }.bind(this),
              );
              n.push(r);
            }.bind(this),
          ),
          Promise.all(n)
        );
      }
      createCssFile(t) {
        if (w.a.isAbsolute(t))
          return new Promise(function (t) {
            t();
          });
        var e,
          n = this.settings.resolver(t);
        e = this.settings.archive
          ? this.settings.archive.getText(n)
          : this.settings.request(n, "text");
        var i = this.urls.map((t) => {
          var e = this.settings.resolver(t);
          return new a.a(n).relative(e);
        });
        return e
          ? e.then(
              (t) => (
                (t = Object(u.e)(t, i, this.replacementUrls)),
                "base64" === this.settings.replacements
                  ? Object(s.createBase64Url)(t, "text/css")
                  : Object(s.createBlobUrl)(t, "text/css")
              ),
              (t) =>
                new Promise(function (t) {
                  t();
                }),
            )
          : new Promise(function (t) {
              t();
            });
      }
      relativeTo(t, e) {
        return (
          (e = e || this.settings.resolver),
          this.urls.map(
            function (n) {
              var i = e(n);
              return new a.a(t).relative(i);
            }.bind(this),
          )
        );
      }
      get(t) {
        var e = this.urls.indexOf(t);
        if (-1 !== e)
          return this.replacementUrls.length
            ? new Promise(
                function (t, n) {
                  t(this.replacementUrls[e]);
                }.bind(this),
              )
            : this.createUrl(t);
      }
      substitute(t, e) {
        var n;
        return (
          (n = e ? this.relativeTo(e) : this.urls),
          Object(u.e)(t, n, this.replacementUrls)
        );
      }
      destroy() {
        ((this.settings = void 0),
          (this.manifest = void 0),
          (this.resources = void 0),
          (this.replacementUrls = void 0),
          (this.html = void 0),
          (this.assets = void 0),
          (this.css = void 0),
          (this.urls = void 0),
          (this.cssUrls = void 0));
      }
    };
    var A = class {
        constructor(t) {
          ((this.pages = []),
            (this.locations = []),
            (this.epubcfi = new h.a()),
            (this.firstPage = 0),
            (this.lastPage = 0),
            (this.totalPages = 0),
            (this.toc = void 0),
            (this.ncx = void 0),
            t && (this.pageList = this.parse(t)),
            this.pageList &&
              this.pageList.length &&
              this.process(this.pageList));
        }
        parse(t) {
          var e = Object(s.qs)(t, "html"),
            n = Object(s.qs)(t, "ncx");
          return e ? this.parseNav(t) : n ? this.parseNcx(t) : void 0;
        }
        parseNav(t) {
          var e,
            n,
            i = Object(s.querySelectorByType)(t, "nav", "page-list"),
            r = i ? Object(s.qsa)(i, "li") : [],
            o = r.length,
            a = [];
          if (!r || 0 === o) return a;
          for (e = 0; e < o; ++e) ((n = this.item(r[e])), a.push(n));
          return a;
        }
        parseNcx(t) {
          var e,
            n,
            i,
            r,
            o = [],
            a = 0;
          if (!(n = Object(s.qs)(t, "pageList"))) return o;
          if (
            ((r = (i = Object(s.qsa)(n, "pageTarget")).length),
            !i || 0 === i.length)
          )
            return o;
          for (a = 0; a < r; ++a) ((e = this.ncxItem(i[a])), o.push(e));
          return o;
        }
        ncxItem(t) {
          var e = Object(s.qs)(t, "navLabel"),
            n = Object(s.qs)(e, "text").textContent;
          return {
            href: Object(s.qs)(t, "content").getAttribute("src"),
            page: parseInt(n, 10),
          };
        }
        item(t) {
          var e,
            n,
            i = Object(s.qs)(t, "a"),
            r = i.getAttribute("href") || "",
            o = i.textContent || "",
            a = parseInt(o);
          return -1 != r.indexOf("epubcfi")
            ? ((n = (e = r.split("#"))[0]),
              {
                cfi: e.length > 1 && e[1],
                href: r,
                packageUrl: n,
                page: a,
              })
            : {
                href: r,
                page: a,
              };
        }
        process(t) {
          (t.forEach(function (t) {
            (this.pages.push(t.page), t.cfi && this.locations.push(t.cfi));
          }, this),
            (this.firstPage = parseInt(this.pages[0])),
            (this.lastPage = parseInt(this.pages[this.pages.length - 1])),
            (this.totalPages = this.lastPage - this.firstPage));
        }
        pageFromCfi(t) {
          var e = -1;
          if (0 === this.locations.length) return -1;
          var n = Object(s.indexOfSorted)(
            t,
            this.locations,
            this.epubcfi.compare,
          );
          return (
            -1 != n
              ? (e = this.pages[n])
              : void 0 !==
                  (e =
                    (n = Object(s.locationOf)(
                      t,
                      this.locations,
                      this.epubcfi.compare,
                    )) -
                      1 >=
                    0
                      ? this.pages[n - 1]
                      : this.pages[0]) || (e = -1),
            e
          );
        }
        cfiFromPage(t) {
          var e = -1;
          "number" != typeof t && (t = parseInt(t));
          var n = this.pages.indexOf(t);
          return (-1 != n && (e = this.locations[n]), e);
        }
        pageFromPercentage(t) {
          return Math.round(this.totalPages * t);
        }
        percentageFromPage(t) {
          var e = (t - this.firstPage) / this.totalPages;
          return Math.round(1e3 * e) / 1e3;
        }
        percentageFromCfi(t) {
          var e = this.pageFromCfi(t);
          return this.percentageFromPage(e);
        }
        destroy() {
          ((this.pages = void 0),
            (this.locations = void 0),
            (this.epubcfi = void 0),
            (this.pageList = void 0),
            (this.toc = void 0),
            (this.ncx = void 0));
        }
      },
      N = n(11),
      O = n(31),
      I = n.n(O);
    var R = class {
        constructor() {
          ((this.zip = void 0), (this.urlCache = {}), this.checkRequirements());
        }
        checkRequirements() {
          try {
            this.zip = new I.a();
          } catch (t) {
            throw new Error("JSZip lib not loaded");
          }
        }
        open(t, e) {
          return this.zip.loadAsync(t, {
            base64: e,
          });
        }
        openUrl(t, e) {
          return c(t, "binary").then(
            function (t) {
              return this.zip.loadAsync(t, {
                base64: e,
              });
            }.bind(this),
          );
        }
        request(t, e) {
          var n,
            i = new s.defer(),
            r = new a.a(t);
          return (
            e || (e = r.extension),
            (n = "blob" == e ? this.getBlob(t) : this.getText(t))
              ? n.then(
                  function (t) {
                    let n = this.handleResponse(t, e);
                    i.resolve(n);
                  }.bind(this),
                )
              : i.reject({
                  message: "File not found in the epub: " + t,
                  stack: new Error().stack,
                }),
            i.promise
          );
        }
        handleResponse(t, e) {
          return "json" == e
            ? JSON.parse(t)
            : Object(s.isXml)(e)
              ? Object(s.parse)(t, "text/xml")
              : "xhtml" == e
                ? Object(s.parse)(t, "application/xhtml+xml")
                : "html" == e || "htm" == e
                  ? Object(s.parse)(t, "text/html")
                  : t;
        }
        getBlob(t, e) {
          var n = window.decodeURIComponent(t.substr(1)),
            i = this.zip.file(n);
          if (i)
            return (
              (e = e || C.lookup(i.name)),
              i.async("uint8array").then(function (t) {
                return new Blob([t], {
                  type: e,
                });
              })
            );
        }
        getText(t, e) {
          var n = window.decodeURIComponent(t.substr(1)),
            i = this.zip.file(n);
          if (i)
            return i.async("string").then(function (t) {
              return t;
            });
        }
        getBase64(t, e) {
          var n = window.decodeURIComponent(t.substr(1)),
            i = this.zip.file(n);
          if (i)
            return (
              (e = e || C.lookup(i.name)),
              i.async("base64").then(function (t) {
                return "data:" + e + ";base64," + t;
              })
            );
        }
        createUrl(t, e) {
          var n,
            i,
            r = new s.defer(),
            o = window.URL || window.webkitURL || window.mozURL,
            a = e && e.base64;
          return t in this.urlCache
            ? (r.resolve(this.urlCache[t]), r.promise)
            : (a
                ? (i = this.getBase64(t)) &&
                  i.then(
                    function (e) {
                      ((this.urlCache[t] = e), r.resolve(e));
                    }.bind(this),
                  )
                : (i = this.getBlob(t)) &&
                  i.then(
                    function (e) {
                      ((n = o.createObjectURL(e)),
                        (this.urlCache[t] = n),
                        r.resolve(n));
                    }.bind(this),
                  ),
              i ||
                r.reject({
                  message: "File not found in the epub: " + t,
                  stack: new Error().stack,
                }),
              r.promise);
        }
        revokeUrl(t) {
          var e = window.URL || window.webkitURL || window.mozURL,
            n = this.urlCache[t];
          n && e.revokeObjectURL(n);
        }
        destroy() {
          var t = window.URL || window.webkitURL || window.mozURL;
          for (let e in this.urlCache) t.revokeObjectURL(e);
          ((this.zip = void 0), (this.urlCache = {}));
        }
      },
      D = n(24),
      L = n.n(D);
    class j {
      constructor(t, e, n) {
        ((this.urlCache = {}),
          (this.storage = void 0),
          (this.name = t),
          (this.requester = e || c),
          (this.resolver = n),
          (this.online = !0),
          this.checkRequirements(),
          this.addListeners());
      }
      checkRequirements() {
        try {
          let t;
          (void 0 === L.a && (t = L.a),
            (this.storage = t.createInstance({
              name: this.name,
            })));
        } catch (t) {
          throw new Error("localForage lib not loaded");
        }
      }
      addListeners() {
        ((this._status = this.status.bind(this)),
          window.addEventListener("online", this._status),
          window.addEventListener("offline", this._status));
      }
      removeListeners() {
        (window.removeEventListener("online", this._status),
          window.removeEventListener("offline", this._status),
          (this._status = void 0));
      }
      status(t) {
        let e = navigator.onLine;
        ((this.online = e),
          e ? this.emit("online", this) : this.emit("offline", this));
      }
      add(t, e) {
        let n = t.resources.map((t) => {
          let { href: n } = t,
            i = this.resolver(n),
            r = window.encodeURIComponent(i);
          return this.storage
            .getItem(r)
            .then((t) =>
              !t || e
                ? this.requester(i, "binary").then((t) =>
                    this.storage.setItem(r, t),
                  )
                : t,
            );
        });
        return Promise.all(n);
      }
      put(t, e, n) {
        let i = window.encodeURIComponent(t);
        return this.storage
          .getItem(i)
          .then(
            (r) =>
              r ||
              this.requester(t, "binary", e, n).then((t) =>
                this.storage.setItem(i, t),
              ),
          );
      }
      request(t, e, n, i) {
        return this.online
          ? this.requester(t, e, n, i).then((e) => (this.put(t), e))
          : this.retrieve(t, e);
      }
      retrieve(t, e) {
        new s.defer();
        var n = new a.a(t);
        return (
          e || (e = n.extension),
          ("blob" == e ? this.getBlob(t) : this.getText(t)).then((n) => {
            var i,
              r = new s.defer();
            return (
              n
                ? ((i = this.handleResponse(n, e)), r.resolve(i))
                : r.reject({
                    message: "File not found in storage: " + t,
                    stack: new Error().stack,
                  }),
              r.promise
            );
          })
        );
      }
      handleResponse(t, e) {
        return "json" == e
          ? JSON.parse(t)
          : Object(s.isXml)(e)
            ? Object(s.parse)(t, "text/xml")
            : "xhtml" == e
              ? Object(s.parse)(t, "application/xhtml+xml")
              : "html" == e || "htm" == e
                ? Object(s.parse)(t, "text/html")
                : t;
      }
      getBlob(t, e) {
        let n = window.encodeURIComponent(t);
        return this.storage.getItem(n).then(function (n) {
          if (n)
            return (
              (e = e || C.lookup(t)),
              new Blob([n], {
                type: e,
              })
            );
        });
      }
      getText(t, e) {
        let n = window.encodeURIComponent(t);
        return (
          (e = e || C.lookup(t)),
          this.storage.getItem(n).then(function (t) {
            var n,
              i = new s.defer(),
              r = new FileReader();
            if (t)
              return (
                (n = new Blob([t], {
                  type: e,
                })),
                r.addEventListener("loadend", () => {
                  i.resolve(r.result);
                }),
                r.readAsText(n, e),
                i.promise
              );
          })
        );
      }
      getBase64(t, e) {
        let n = window.encodeURIComponent(t);
        return (
          (e = e || C.lookup(t)),
          this.storage.getItem(n).then((t) => {
            var n,
              i = new s.defer(),
              r = new FileReader();
            if (t)
              return (
                (n = new Blob([t], {
                  type: e,
                })),
                r.addEventListener("loadend", () => {
                  i.resolve(r.result);
                }),
                r.readAsDataURL(n, e),
                i.promise
              );
          })
        );
      }
      createUrl(t, e) {
        var n,
          i,
          r = new s.defer(),
          o = window.URL || window.webkitURL || window.mozURL,
          a = e && e.base64;
        return t in this.urlCache
          ? (r.resolve(this.urlCache[t]), r.promise)
          : (a
              ? (i = this.getBase64(t)) &&
                i.then(
                  function (e) {
                    ((this.urlCache[t] = e), r.resolve(e));
                  }.bind(this),
                )
              : (i = this.getBlob(t)) &&
                i.then(
                  function (e) {
                    ((n = o.createObjectURL(e)),
                      (this.urlCache[t] = n),
                      r.resolve(n));
                  }.bind(this),
                ),
            i ||
              r.reject({
                message: "File not found in storage: " + t,
                stack: new Error().stack,
              }),
            r.promise);
      }
      revokeUrl(t) {
        var e = window.URL || window.webkitURL || window.mozURL,
          n = this.urlCache[t];
        n && e.revokeObjectURL(n);
      }
      destroy() {
        var t = window.URL || window.webkitURL || window.mozURL;
        for (let e in this.urlCache) t.revokeObjectURL(e);
        ((this.urlCache = {}), this.removeListeners());
      }
    }
    r()(j.prototype);
    var z = j;
    var P = class {
      constructor(t) {
        ((this.interactive = ""),
          (this.fixedLayout = ""),
          (this.openToSpread = ""),
          (this.orientationLock = ""),
          t && this.parse(t));
      }
      parse(t) {
        if (!t) return this;
        const e = Object(s.qs)(t, "display_options");
        if (!e) return this;
        return (
          Object(s.qsa)(e, "option").forEach((t) => {
            let e = "";
            switch (
              (t.childNodes.length && (e = t.childNodes[0].nodeValue),
              t.attributes.name.value)
            ) {
              case "interactive":
                this.interactive = e;
                break;
              case "fixed-layout":
                this.fixedLayout = e;
                break;
              case "open-to-spread":
                this.openToSpread = e;
                break;
              case "orientation-lock":
                this.orientationLock = e;
            }
          }),
          this
        );
      }
      destroy() {
        ((this.interactive = void 0),
          (this.fixedLayout = void 0),
          (this.openToSpread = void 0),
          (this.orientationLock = void 0));
      }
    };
    const B = "binary",
      M = "base64",
      F = "epub",
      U = "opf",
      q = "json",
      W = "directory";
    class H {
      constructor(t, e) {
        (void 0 === e &&
          "string" != typeof t &&
          t instanceof Blob == !1 &&
          t instanceof ArrayBuffer == !1 &&
          ((e = t), (t = void 0)),
          (this.settings = Object(s.extend)(this.settings || {}, {
            requestMethod: void 0,
            requestCredentials: void 0,
            requestHeaders: void 0,
            encoding: void 0,
            replacements: void 0,
            canonical: void 0,
            openAs: void 0,
            store: void 0,
          })),
          Object(s.extend)(this.settings, e),
          (this.opening = new s.defer()),
          (this.opened = this.opening.promise),
          (this.isOpen = !1),
          (this.loading = {
            manifest: new s.defer(),
            spine: new s.defer(),
            metadata: new s.defer(),
            cover: new s.defer(),
            navigation: new s.defer(),
            pageList: new s.defer(),
            resources: new s.defer(),
            displayOptions: new s.defer(),
          }),
          (this.loaded = {
            manifest: this.loading.manifest.promise,
            spine: this.loading.spine.promise,
            metadata: this.loading.metadata.promise,
            cover: this.loading.cover.promise,
            navigation: this.loading.navigation.promise,
            pageList: this.loading.pageList.promise,
            resources: this.loading.resources.promise,
            displayOptions: this.loading.displayOptions.promise,
          }),
          (this.ready = Promise.all([
            this.loaded.manifest,
            this.loaded.spine,
            this.loaded.metadata,
            this.loaded.cover,
            this.loaded.navigation,
            this.loaded.resources,
            this.loaded.displayOptions,
          ])),
          (this.isRendered = !1),
          (this.request = this.settings.requestMethod || c),
          (this.spine = new p()),
          (this.locations = new y(this.spine, this.load.bind(this))),
          (this.navigation = void 0),
          (this.pageList = void 0),
          (this.url = void 0),
          (this.path = void 0),
          (this.archived = !1),
          (this.archive = void 0),
          (this.storage = void 0),
          (this.resources = void 0),
          (this.rendition = void 0),
          (this.container = void 0),
          (this.packaging = void 0),
          (this.displayOptions = void 0),
          this.settings.store && this.store(this.settings.store),
          t &&
            this.open(t, this.settings.openAs).catch((e) => {
              var n = new Error("Cannot load book at " + t);
              this.emit(m.c.BOOK.OPEN_FAILED, n);
            }));
      }
      open(t, e) {
        var n,
          i = e || this.determineType(t);
        return (
          i === B
            ? ((this.archived = !0),
              (this.url = new o.a("/", "")),
              (n = this.openEpub(t)))
            : i === M
              ? ((this.archived = !0),
                (this.url = new o.a("/", "")),
                (n = this.openEpub(t, i)))
              : i === F
                ? ((this.archived = !0),
                  (this.url = new o.a("/", "")),
                  (n = this.request(
                    t,
                    "binary",
                    this.settings.requestCredentials,
                    this.settings.requestHeaders,
                  ).then(this.openEpub.bind(this))))
                : i == U
                  ? ((this.url = new o.a(t)),
                    (n = this.openPackaging(this.url.Path.toString())))
                  : i == q
                    ? ((this.url = new o.a(t)),
                      (n = this.openManifest(this.url.Path.toString())))
                    : ((this.url = new o.a(t)),
                      (n = this.openContainer("META-INF/container.xml").then(
                        this.openPackaging.bind(this),
                      ))),
          n
        );
      }
      openEpub(t, e) {
        return this.unarchive(t, e || this.settings.encoding)
          .then(() => this.openContainer("META-INF/container.xml"))
          .then((t) => this.openPackaging(t));
      }
      openContainer(t) {
        return this.load(t).then(
          (t) => (
            (this.container = new x(t)),
            this.resolve(this.container.packagePath)
          ),
        );
      }
      openPackaging(t) {
        return (
          (this.path = new a.a(t)),
          this.load(t).then(
            (t) => ((this.packaging = new _(t)), this.unpack(this.packaging)),
          )
        );
      }
      openManifest(t) {
        return (
          (this.path = new a.a(t)),
          this.load(t).then(
            (t) => (
              (this.packaging = new _()),
              this.packaging.load(t),
              this.unpack(this.packaging)
            ),
          )
        );
      }
      load(t) {
        var e = this.resolve(t);
        return this.archived
          ? this.archive.request(e)
          : this.request(
              e,
              null,
              this.settings.requestCredentials,
              this.settings.requestHeaders,
            );
      }
      resolve(t, e) {
        if (t) {
          var n = t;
          return t.indexOf("://") > -1
            ? t
            : (this.path && (n = this.path.resolve(t)),
              0 != e && this.url && (n = this.url.resolve(n)),
              n);
        }
      }
      canonical(t) {
        return t
          ? this.settings.canonical
            ? this.settings.canonical(t)
            : this.resolve(t, !0)
          : "";
      }
      determineType(t) {
        var e;
        return "base64" === this.settings.encoding
          ? M
          : "string" != typeof t
            ? B
            : ((e = new o.a(t).path().extension) &&
                (e = e.replace(/\?.*$/, "")),
              e
                ? "epub" === e
                  ? F
                  : "opf" === e
                    ? U
                    : "json" === e
                      ? q
                      : void 0
                : W);
      }
      unpack(t) {
        ((this.package = t),
          "" === this.packaging.metadata.layout
            ? this.load(
                this.url.resolve(
                  "META-INF/com.apple.ibooks.display-options.xml",
                ),
              )
                .then((t) => {
                  ((this.displayOptions = new P(t)),
                    this.loading.displayOptions.resolve(this.displayOptions));
                })
                .catch((t) => {
                  ((this.displayOptions = new P()),
                    this.loading.displayOptions.resolve(this.displayOptions));
                })
            : ((this.displayOptions = new P()),
              this.loading.displayOptions.resolve(this.displayOptions)),
          this.spine.unpack(
            this.packaging,
            this.resolve.bind(this),
            this.canonical.bind(this),
          ),
          (this.resources = new T(this.packaging.manifest, {
            archive: this.archive,
            resolver: this.resolve.bind(this),
            request: this.request.bind(this),
            replacements:
              this.settings.replacements ||
              (this.archived ? "blobUrl" : "base64"),
          })),
          this.loadNavigation(this.packaging).then(() => {
            this.loading.navigation.resolve(this.navigation);
          }),
          this.packaging.coverPath &&
            (this.cover = this.resolve(this.packaging.coverPath)),
          this.loading.manifest.resolve(this.packaging.manifest),
          this.loading.metadata.resolve(this.packaging.metadata),
          this.loading.spine.resolve(this.spine),
          this.loading.cover.resolve(this.cover),
          this.loading.resources.resolve(this.resources),
          this.loading.pageList.resolve(this.pageList),
          (this.isOpen = !0),
          this.archived ||
          (this.settings.replacements && "none" != this.settings.replacements)
            ? this.replacements()
                .then(() => {
                  this.loaded.displayOptions.then(() => {
                    this.opening.resolve(this);
                  });
                })
                .catch((t) => {
                  console.error(t);
                })
            : this.loaded.displayOptions.then(() => {
                this.opening.resolve(this);
              }));
      }
      loadNavigation(t) {
        let e = t.navPath || t.ncxPath,
          n = t.toc;
        return n
          ? new Promise((e, i) => {
              ((this.navigation = new E(n)),
                t.pageList && (this.pageList = new A(t.pageList)),
                e(this.navigation));
            })
          : e
            ? this.load(e, "xml").then(
                (t) => (
                  (this.navigation = new E(t)),
                  (this.pageList = new A(t)),
                  this.navigation
                ),
              )
            : new Promise((t, e) => {
                ((this.navigation = new E()),
                  (this.pageList = new A()),
                  t(this.navigation));
              });
      }
      section(t) {
        return this.spine.get(t);
      }
      renderTo(t, e) {
        return (
          (this.rendition = new N.a(this, e)),
          this.rendition.attachTo(t),
          this.rendition
        );
      }
      setRequestCredentials(t) {
        this.settings.requestCredentials = t;
      }
      setRequestHeaders(t) {
        this.settings.requestHeaders = t;
      }
      unarchive(t, e) {
        return ((this.archive = new R()), this.archive.open(t, e));
      }
      store(t) {
        let e =
            this.settings.replacements && "none" !== this.settings.replacements,
          n = this.url,
          i = this.settings.requestMethod || c.bind(this);
        return (
          (this.storage = new z(t, i, this.resolve.bind(this))),
          (this.request = this.storage.request.bind(this.storage)),
          this.opened.then(() => {
            this.archived &&
              (this.storage.requester = this.archive.request.bind(
                this.archive,
              ));
            let t = (t, e) => {
              e.output = this.resources.substitute(t, e.url);
            };
            ((this.resources.settings.replacements = e || "blobUrl"),
              this.resources
                .replacements()
                .then(() => this.resources.replaceCss()),
              this.storage.on("offline", () => {
                ((this.url = new o.a("/", "")),
                  this.spine.hooks.serialize.register(t));
              }),
              this.storage.on("online", () => {
                ((this.url = n), this.spine.hooks.serialize.deregister(t));
              }));
          }),
          this.storage
        );
      }
      coverUrl() {
        return this.loaded.cover.then(() =>
          this.cover
            ? this.archived
              ? this.archive.createUrl(this.cover)
              : this.cover
            : null,
        );
      }
      replacements() {
        return (
          this.spine.hooks.serialize.register((t, e) => {
            e.output = this.resources.substitute(t, e.url);
          }),
          this.resources.replacements().then(() => this.resources.replaceCss())
        );
      }
      getRange(t) {
        var e = new h.a(t),
          n = this.spine.get(e.spinePos),
          i = this.load.bind(this);
        return n
          ? n.load(i).then(function (t) {
              return e.toRange(n.document);
            })
          : new Promise((t, e) => {
              e("CFI could not be found");
            });
      }
      key(t) {
        var e = t || this.packaging.metadata.identifier || this.url.filename;
        return `epubjs:${m.b}:${e}`;
      }
      destroy() {
        ((this.opened = void 0),
          (this.loading = void 0),
          (this.loaded = void 0),
          (this.ready = void 0),
          (this.isOpen = !1),
          (this.isRendered = !1),
          this.spine && this.spine.destroy(),
          this.locations && this.locations.destroy(),
          this.pageList && this.pageList.destroy(),
          this.archive && this.archive.destroy(),
          this.resources && this.resources.destroy(),
          this.container && this.container.destroy(),
          this.packaging && this.packaging.destroy(),
          this.rendition && this.rendition.destroy(),
          this.displayOptions && this.displayOptions.destroy(),
          (this.spine = void 0),
          (this.locations = void 0),
          (this.pageList = void 0),
          (this.archive = void 0),
          (this.resources = void 0),
          (this.container = void 0),
          (this.packaging = void 0),
          (this.rendition = void 0),
          (this.navigation = void 0),
          (this.url = void 0),
          (this.path = void 0),
          (this.archived = !1));
      }
    }
    r()(H.prototype);
    e.a = H;
  },
  16: function (t, e, n) {
    "use strict";
    (Object.defineProperty(e, "__esModule", {
      value: !0,
    }),
      (e.Underline = e.Highlight = e.Mark = e.Pane = void 0));
    var i = (function () {
        function t(t, e) {
          for (var n = 0; n < e.length; n++) {
            var i = e[n];
            ((i.enumerable = i.enumerable || !1),
              (i.configurable = !0),
              "value" in i && (i.writable = !0),
              Object.defineProperty(t, i.key, i));
          }
        }
        return function (e, n, i) {
          return (n && t(e.prototype, n), i && t(e, i), e);
        };
      })(),
      r = o(n(53)),
      s = o(n(54));
    function o(t) {
      return t && t.__esModule
        ? t
        : {
            default: t,
          };
    }
    function a(t, e) {
      if (!t)
        throw new ReferenceError(
          "this hasn't been initialised - super() hasn't been called",
        );
      return !e || ("object" != typeof e && "function" != typeof e) ? t : e;
    }
    function h(t, e) {
      if ("function" != typeof e && null !== e)
        throw new TypeError(
          "Super expression must either be null or a function, not " + typeof e,
        );
      ((t.prototype = Object.create(e && e.prototype, {
        constructor: {
          value: t,
          enumerable: !1,
          writable: !0,
          configurable: !0,
        },
      })),
        e &&
          (Object.setPrototypeOf
            ? Object.setPrototypeOf(t, e)
            : (t.__proto__ = e)));
    }
    function l(t, e) {
      if (!(t instanceof e))
        throw new TypeError("Cannot call a class as a function");
    }
    e.Pane = (function () {
      function t(e) {
        var n =
          arguments.length > 1 && void 0 !== arguments[1]
            ? arguments[1]
            : document.body;
        (l(this, t),
          (this.target = e),
          (this.element = r.default.createElement("svg")),
          (this.marks = []),
          (this.element.style.position = "absolute"),
          this.element.setAttribute("pointer-events", "none"),
          s.default.proxyMouse(this.target, this.marks),
          (this.container = n),
          this.container.appendChild(this.element),
          this.render());
      }
      return (
        i(t, [
          {
            key: "addMark",
            value: function (t) {
              var e = r.default.createElement("g");
              return (
                this.element.appendChild(e),
                t.bind(e, this.container),
                this.marks.push(t),
                t.render(),
                t
              );
            },
          },
          {
            key: "removeMark",
            value: function (t) {
              var e = this.marks.indexOf(t);
              if (-1 !== e) {
                var n = t.unbind();
                (this.element.removeChild(n), this.marks.splice(e, 1));
              }
            },
          },
          {
            key: "render",
            value: function () {
              var t, e, n, i;
              !(function (t, e) {
                (t.style.setProperty("top", e.top + "px", "important"),
                  t.style.setProperty("left", e.left + "px", "important"),
                  t.style.setProperty("height", e.height + "px", "important"),
                  t.style.setProperty("width", e.width + "px", "important"));
              })(
                this.element,
                ((t = this.target),
                (e = this.container),
                (n = e.getBoundingClientRect()),
                (i = t.getBoundingClientRect()),
                {
                  top: i.top - n.top,
                  left: i.left - n.left,
                  height: t.scrollHeight,
                  width: t.scrollWidth,
                }),
              );
              var r = !0,
                s = !1,
                o = void 0;
              try {
                for (
                  var a, h = this.marks[Symbol.iterator]();
                  !(r = (a = h.next()).done);
                  r = !0
                ) {
                  a.value.render();
                }
              } catch (t) {
                ((s = !0), (o = t));
              } finally {
                try {
                  !r && h.return && h.return();
                } finally {
                  if (s) throw o;
                }
              }
            },
          },
        ]),
        t
      );
    })();
    var u = (e.Mark = (function () {
        function t() {
          (l(this, t), (this.element = null));
        }
        return (
          i(t, [
            {
              key: "bind",
              value: function (t, e) {
                ((this.element = t), (this.container = e));
              },
            },
            {
              key: "unbind",
              value: function () {
                var t = this.element;
                return ((this.element = null), t);
              },
            },
            {
              key: "render",
              value: function () {},
            },
            {
              key: "dispatchEvent",
              value: function (t) {
                this.element && this.element.dispatchEvent(t);
              },
            },
            {
              key: "getBoundingClientRect",
              value: function () {
                return this.element.getBoundingClientRect();
              },
            },
            {
              key: "getClientRects",
              value: function () {
                for (var t = [], e = this.element.firstChild; e; )
                  (t.push(e.getBoundingClientRect()), (e = e.nextSibling));
                return t;
              },
            },
            {
              key: "filteredRanges",
              value: function () {
                var t = Array.from(this.range.getClientRects());
                return t.filter(function (e) {
                  for (var n = 0; n < t.length; n++) {
                    if (t[n] === e) return !0;
                    if (
                      ((i = t[n]),
                      (r = e).right <= i.right &&
                        r.left >= i.left &&
                        r.top >= i.top &&
                        r.bottom <= i.bottom)
                    )
                      return !1;
                  }
                  var i, r;
                  return !0;
                });
              },
            },
          ]),
          t
        );
      })()),
      c = (e.Highlight = (function (t) {
        function e(t, n, i, r) {
          l(this, e);
          var s = a(this, (e.__proto__ || Object.getPrototypeOf(e)).call(this));
          return (
            (s.range = t),
            (s.className = n),
            (s.data = i || {}),
            (s.attributes = r || {}),
            s
          );
        }
        return (
          h(e, t),
          i(e, [
            {
              key: "bind",
              value: function (t, n) {
                for (var i in ((function t(e, n, i) {
                  null === e && (e = Function.prototype);
                  var r = Object.getOwnPropertyDescriptor(e, n);
                  if (void 0 === r) {
                    var s = Object.getPrototypeOf(e);
                    return null === s ? void 0 : t(s, n, i);
                  }
                  if ("value" in r) return r.value;
                  var o = r.get;
                  return void 0 !== o ? o.call(i) : void 0;
                })(
                  e.prototype.__proto__ || Object.getPrototypeOf(e.prototype),
                  "bind",
                  this,
                ).call(this, t, n),
                this.data))
                  this.data.hasOwnProperty(i) &&
                    (this.element.dataset[i] = this.data[i]);
                for (var i in this.attributes)
                  this.attributes.hasOwnProperty(i) &&
                    this.element.setAttribute(i, this.attributes[i]);
                this.className && this.element.classList.add(this.className);
              },
            },
            {
              key: "render",
              value: function () {
                for (; this.element.firstChild; )
                  this.element.removeChild(this.element.firstChild);
                for (
                  var t = this.element.ownerDocument.createDocumentFragment(),
                    e = this.filteredRanges(),
                    n = this.element.getBoundingClientRect(),
                    i = this.container.getBoundingClientRect(),
                    s = 0,
                    o = e.length;
                  s < o;
                  s++
                ) {
                  var a = e[s],
                    h = r.default.createElement("rect");
                  (h.setAttribute("x", a.left - n.left + i.left),
                    h.setAttribute("y", a.top - n.top + i.top),
                    h.setAttribute("height", a.height),
                    h.setAttribute("width", a.width),
                    t.appendChild(h));
                }
                this.element.appendChild(t);
              },
            },
          ]),
          e
        );
      })(u));
    e.Underline = (function (t) {
      function e(t, n, i, r) {
        return (
          l(this, e),
          a(
            this,
            (e.__proto__ || Object.getPrototypeOf(e)).call(this, t, n, i, r),
          )
        );
      }
      return (
        h(e, t),
        i(e, [
          {
            key: "render",
            value: function () {
              for (; this.element.firstChild; )
                this.element.removeChild(this.element.firstChild);
              for (
                var t = this.element.ownerDocument.createDocumentFragment(),
                  e = this.filteredRanges(),
                  n = this.element.getBoundingClientRect(),
                  i = this.container.getBoundingClientRect(),
                  s = 0,
                  o = e.length;
                s < o;
                s++
              ) {
                var a = e[s],
                  h = r.default.createElement("rect");
                (h.setAttribute("x", a.left - n.left + i.left),
                  h.setAttribute("y", a.top - n.top + i.top),
                  h.setAttribute("height", a.height),
                  h.setAttribute("width", a.width),
                  h.setAttribute("fill", "none"));
                var l = r.default.createElement("line");
                (l.setAttribute("x1", a.left - n.left + i.left),
                  l.setAttribute("x2", a.left - n.left + i.left + a.width),
                  l.setAttribute("y1", a.top - n.top + i.top + a.height - 1),
                  l.setAttribute("y2", a.top - n.top + i.top + a.height - 1),
                  l.setAttribute("stroke-width", 1),
                  l.setAttribute("stroke", "black"),
                  l.setAttribute("stroke-linecap", "square"),
                  t.appendChild(h),
                  t.appendChild(l));
              }
              this.element.appendChild(t);
            },
          },
        ]),
        e
      );
    })(c);
  },
  17: function (t, e, n) {
    "use strict";
    var i = n(0),
      r = n(1),
      s = n(3),
      o = n.n(s);
    class a {
      constructor(t) {
        ((this.settings = t),
          (this.name = t.layout || "reflowable"),
          (this._spread = "none" !== t.spread),
          (this._minSpreadWidth = t.minSpreadWidth || 800),
          (this._evenSpreads = t.evenSpreads || !1),
          "scrolled" === t.flow ||
          "scrolled-continuous" === t.flow ||
          "scrolled-doc" === t.flow
            ? (this._flow = "scrolled")
            : (this._flow = "paginated"),
          (this.width = 0),
          (this.height = 0),
          (this.spreadWidth = 0),
          (this.delta = 0),
          (this.columnWidth = 0),
          (this.gap = 0),
          (this.divisor = 1),
          (this.props = {
            name: this.name,
            spread: this._spread,
            flow: this._flow,
            width: 0,
            height: 0,
            spreadWidth: 0,
            delta: 0,
            columnWidth: 0,
            gap: 0,
            divisor: 1,
          }));
      }
      flow(t) {
        return (
          void 0 !== t &&
            ((this._flow =
              "scrolled" === t ||
              "scrolled-continuous" === t ||
              "scrolled-doc" === t
                ? "scrolled"
                : "paginated"),
            this.update({
              flow: this._flow,
            })),
          this._flow
        );
      }
      spread(t, e) {
        return (
          t &&
            ((this._spread = "none" !== t),
            this.update({
              spread: this._spread,
            })),
          e >= 0 && (this._minSpreadWidth = e),
          this._spread
        );
      }
      calculate(t, e, n) {
        var i,
          r,
          s,
          o,
          a = 1,
          h = n || 0,
          l = t,
          u = e,
          c = Math.floor(l / 12);
        ((a = this._spread && l >= this._minSpreadWidth ? 2 : 1),
          "reflowable" !== this.name ||
            "paginated" !== this._flow ||
            n >= 0 ||
            (h = c % 2 == 0 ? c : c - 1),
          "pre-paginated" === this.name && (h = 0),
          a > 1 ? (s = (i = l / a - h) + h) : ((i = l), (s = l)),
          "pre-paginated" === this.name && a > 1 && (l = i),
          (r = i * a + h),
          (o = l),
          (this.width = l),
          (this.height = u),
          (this.spreadWidth = r),
          (this.pageWidth = s),
          (this.delta = o),
          (this.columnWidth = i),
          (this.gap = h),
          (this.divisor = a),
          this.update({
            width: l,
            height: u,
            spreadWidth: r,
            pageWidth: s,
            delta: o,
            columnWidth: i,
            gap: h,
            divisor: a,
          }));
      }
      format(t, e, n) {
        return "pre-paginated" === this.name
          ? t.fit(this.columnWidth, this.height, e)
          : "paginated" === this._flow
            ? t.columns(
                this.width,
                this.height,
                this.columnWidth,
                this.gap,
                this.settings.direction,
              )
            : n && "horizontal" === n
              ? t.size(null, this.height)
              : t.size(this.width, null);
      }
      count(t, e) {
        let n, i;
        return (
          "pre-paginated" === this.name
            ? ((n = 1), (i = 1))
            : "paginated" === this._flow
              ? ((e = e || this.delta),
                (n = Math.ceil(t / e)),
                (i = n * this.divisor))
              : ((e = e || this.height), (n = Math.ceil(t / e)), (i = n)),
          {
            spreads: n,
            pages: i,
          }
        );
      }
      update(t) {
        if (
          (Object.keys(t).forEach((e) => {
            this.props[e] === t[e] && delete t[e];
          }),
          Object.keys(t).length > 0)
        ) {
          let e = Object(i.extend)(this.props, t);
          this.emit(r.c.LAYOUT.UPDATED, e, t);
        }
      }
    }
    (o()(a.prototype), (e.a = a));
  },
  53: function (t, e, n) {
    "use strict";
    function i(t) {
      return document.createElementNS("http://www.w3.org/2000/svg", t);
    }
    (Object.defineProperty(e, "__esModule", {
      value: !0,
    }),
      (e.createElement = i),
      (e.default = {
        createElement: i,
      }));
  },
  54: function (t, e, n) {
    "use strict";
    function i(t, e) {
      function n(n) {
        for (var i = e.length - 1; i >= 0; i--) {
          var o = e[i],
            a = n.clientX,
            h = n.clientY;
          if (
            (n.touches &&
              n.touches.length &&
              ((a = n.touches[0].clientX), (h = n.touches[0].clientY)),
            s(o, t, a, h))
          ) {
            o.dispatchEvent(r(n));
            break;
          }
        }
      }
      if ("iframe" === t.nodeName || "IFRAME" === t.nodeName)
        try {
          this.target = t.contentDocument;
        } catch (e) {
          this.target = t;
        }
      else this.target = t;
      for (
        var i = ["mouseup", "mousedown", "click", "touchstart"], o = 0;
        o < i.length;
        o++
      ) {
        var a = i[o];
        this.target.addEventListener(
          a,
          function (t) {
            return n(t);
          },
          !1,
        );
      }
    }
    function r(t) {
      var e = Object.assign({}, t, {
        bubbles: !1,
      });
      try {
        return new MouseEvent(t.type, e);
      } catch (i) {
        var n = document.createEvent("MouseEvents");
        return (
          n.initMouseEvent(
            t.type,
            !1,
            e.cancelable,
            e.view,
            e.detail,
            e.screenX,
            e.screenY,
            e.clientX,
            e.clientY,
            e.ctrlKey,
            e.altKey,
            e.shiftKey,
            e.metaKey,
            e.button,
            e.relatedTarget,
          ),
          n
        );
      }
    }
    function s(t, e, n, i) {
      var r = e.getBoundingClientRect();
      function s(t, e, n) {
        var i = t.top - r.top,
          s = t.left - r.left,
          o = i + t.height,
          a = s + t.width;
        return i <= n && s <= e && o > n && a > e;
      }
      if (!s(t.getBoundingClientRect(), n, i)) return !1;
      for (var o = t.getClientRects(), a = 0, h = o.length; a < h; a++)
        if (s(o[a], n, i)) return !0;
      return !1;
    }
    (Object.defineProperty(e, "__esModule", {
      value: !0,
    }),
      (e.proxyMouse = i),
      (e.clone = r),
      (e.default = {
        proxyMouse: i,
      }));
  },
};
