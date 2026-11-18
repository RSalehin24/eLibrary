/**
 * Auto-generated from the EPUB runtime source snapshot.
 * Responsibility: Book navigation, location tracking, and section traversal logic.
 * Module IDs: 19, 20, 21, 22, 23
 */
export const navigationEngineModules = {
  19: function (t, e, n) {
    "use strict";
    var i = n(44)();
    t.exports = function (t) {
      return t !== i && null !== t;
    };
  },
  20: function (t, e) {
    t.exports = function (t) {
      var e = typeof t;
      return null != t && ("object" == e || "function" == e);
    };
  },
  21: function (t, e, n) {
    "use strict";
    var i = n(3),
      r = n.n(i),
      s = n(0),
      o = n(2),
      a = n(10),
      h = n(1),
      l = n(16);
    class u {
      constructor(t, e) {
        ((this.settings = Object(s.extend)(
          {
            ignoreClass: "",
            axis: void 0,
            direction: void 0,
            width: 0,
            height: 0,
            layout: void 0,
            globalLayoutProperties: {},
            method: void 0,
            forceRight: !1,
          },
          e || {},
        )),
          (this.id = "epubjs-view-" + Object(s.uuid)()),
          (this.section = t),
          (this.index = t.index),
          (this.element = this.container(this.settings.axis)),
          (this.added = !1),
          (this.displayed = !1),
          (this.rendered = !1),
          (this.fixedWidth = 0),
          (this.fixedHeight = 0),
          (this.epubcfi = new o.a()),
          (this.layout = this.settings.layout),
          (this.pane = void 0),
          (this.highlights = {}),
          (this.underlines = {}),
          (this.marks = {}));
      }
      container(t) {
        var e = document.createElement("div");
        return (
          e.classList.add("epub-view"),
          (e.style.height = "0px"),
          (e.style.width = "0px"),
          (e.style.overflow = "hidden"),
          (e.style.position = "relative"),
          (e.style.display = "block"),
          (e.style.flex = t && "horizontal" == t ? "none" : "initial"),
          e
        );
      }
      create() {
        return (
          this.iframe ||
            (this.element || (this.element = this.createContainer()),
            (this.iframe = document.createElement("iframe")),
            (this.iframe.id = this.id),
            (this.iframe.scrolling = "no"),
            (this.iframe.style.overflow = "hidden"),
            (this.iframe.seamless = "seamless"),
            (this.iframe.style.border = "none"),
            this.iframe.setAttribute("enable-annotation", "true"),
            (this.resizing = !0),
            (this.element.style.visibility = "hidden"),
            (this.iframe.style.visibility = "hidden"),
            (this.iframe.style.width = "0"),
            (this.iframe.style.height = "0"),
            (this._width = 0),
            (this._height = 0),
            this.element.setAttribute("ref", this.index),
            (this.added = !0),
            (this.elementBounds = Object(s.bounds)(this.element)),
            "srcdoc" in this.iframe
              ? (this.supportsSrcdoc = !0)
              : (this.supportsSrcdoc = !1),
            this.settings.method ||
              (this.settings.method = this.supportsSrcdoc
                ? "srcdoc"
                : "write")),
          this.iframe
        );
      }
      render(t, e) {
        return (
          this.create(),
          this.size(),
          this.sectionRender || (this.sectionRender = this.section.render(t)),
          this.sectionRender
            .then(
              function (t) {
                return this.load(t);
              }.bind(this),
            )
            .then(
              function () {
                let t,
                  e = this.contents.writingMode();
                return (
                  (t =
                    "scrolled" === this.settings.flow
                      ? 0 === e.indexOf("vertical")
                        ? "horizontal"
                        : "vertical"
                      : 0 === e.indexOf("vertical")
                        ? "vertical"
                        : "horizontal"),
                  0 === e.indexOf("vertical") &&
                    "paginated" === this.settings.flow &&
                    (this.layout.delta = this.layout.height),
                  this.setAxis(t),
                  this.emit(h.c.VIEWS.AXIS, t),
                  this.setWritingMode(e),
                  this.emit(h.c.VIEWS.WRITING_MODE, e),
                  this.layout.format(this.contents, this.section, this.axis),
                  this.addListeners(),
                  new Promise((t, e) => {
                    (this.expand(),
                      this.settings.forceRight &&
                        (this.element.style.marginLeft = this.width() + "px"),
                      t());
                  })
                );
              }.bind(this),
              function (t) {
                return (
                  this.emit(h.c.VIEWS.LOAD_ERROR, t),
                  new Promise((e, n) => {
                    n(t);
                  })
                );
              }.bind(this),
            )
            .then(
              function () {
                this.emit(h.c.VIEWS.RENDERED, this.section);
              }.bind(this),
            )
        );
      }
      reset() {
        (this.iframe &&
          ((this.iframe.style.width = "0"),
          (this.iframe.style.height = "0"),
          (this._width = 0),
          (this._height = 0),
          (this._textWidth = void 0),
          (this._contentWidth = void 0),
          (this._textHeight = void 0),
          (this._contentHeight = void 0)),
          (this._needsReframe = !0));
      }
      size(t, e) {
        var n = t || this.settings.width,
          i = e || this.settings.height;
        ("pre-paginated" === this.layout.name
          ? this.lock("both", n, i)
          : "horizontal" === this.settings.axis
            ? this.lock("height", n, i)
            : this.lock("width", n, i),
          (this.settings.width = n),
          (this.settings.height = i));
      }
      lock(t, e, n) {
        var i,
          r = Object(s.borders)(this.element);
        ((i = this.iframe
          ? Object(s.borders)(this.iframe)
          : {
              width: 0,
              height: 0,
            }),
          "width" == t &&
            Object(s.isNumber)(e) &&
            (this.lockedWidth = e - r.width - i.width),
          "height" == t &&
            Object(s.isNumber)(n) &&
            (this.lockedHeight = n - r.height - i.height),
          "both" === t &&
            Object(s.isNumber)(e) &&
            Object(s.isNumber)(n) &&
            ((this.lockedWidth = e - r.width - i.width),
            (this.lockedHeight = n - r.height - i.height)),
          this.displayed && this.iframe && this.expand());
      }
      expand(t) {
        var e,
          n = this.lockedWidth,
          i = this.lockedHeight;
        this.iframe &&
          !this._expanding &&
          ((this._expanding = !0),
          "pre-paginated" === this.layout.name
            ? ((n = this.layout.columnWidth), (i = this.layout.height))
            : "horizontal" === this.settings.axis
              ? ((n = this.contents.textWidth()) % this.layout.pageWidth > 0 &&
                  (n =
                    Math.ceil(n / this.layout.pageWidth) *
                    this.layout.pageWidth),
                this.settings.forceEvenPages &&
                  ((e = n / this.layout.pageWidth),
                  this.layout.divisor > 1 &&
                    "reflowable" === this.layout.name &&
                    e % 2 > 0 &&
                    (n += this.layout.pageWidth)))
              : "vertical" === this.settings.axis &&
                ((i = this.contents.textHeight()),
                "paginated" === this.settings.flow &&
                  i % this.layout.height > 0 &&
                  (i = Math.ceil(i / this.layout.height) * this.layout.height)),
          (this._needsReframe || n != this._width || i != this._height) &&
            this.reframe(n, i),
          (this._expanding = !1));
      }
      reframe(t, e) {
        var n;
        (Object(s.isNumber)(t) &&
          ((this.element.style.width = t + "px"),
          (this.iframe.style.width = t + "px"),
          (this._width = t)),
          Object(s.isNumber)(e) &&
            ((this.element.style.height = e + "px"),
            (this.iframe.style.height = e + "px"),
            (this._height = e)),
          (n = {
            width: t,
            height: e,
            widthDelta: this.prevBounds ? t - this.prevBounds.width : t,
            heightDelta: this.prevBounds ? e - this.prevBounds.height : e,
          }),
          this.pane && this.pane.render(),
          requestAnimationFrame(() => {
            let t;
            for (let e in this.marks)
              this.marks.hasOwnProperty(e) &&
                ((t = this.marks[e]), this.placeMark(t.element, t.range));
          }),
          this.onResize(this, n),
          this.emit(h.c.VIEWS.RESIZED, n),
          (this.prevBounds = n),
          (this.elementBounds = Object(s.bounds)(this.element)));
      }
      load(t) {
        var e = new s.defer(),
          n = e.promise;
        if (!this.iframe)
          return (e.reject(new Error("No Iframe Available")), n);
        if (
          ((this.iframe.onload = function (t) {
            this.onLoad(t, e);
          }.bind(this)),
          "blobUrl" === this.settings.method)
        )
          ((this.blobUrl = Object(s.createBlobUrl)(t, "application/xhtml+xml")),
            (this.iframe.src = this.blobUrl),
            this.element.appendChild(this.iframe));
        else if ("srcdoc" === this.settings.method)
          ((this.iframe.srcdoc = t), this.element.appendChild(this.iframe));
        else {
          if (
            (this.element.appendChild(this.iframe),
            (this.document = this.iframe.contentDocument),
            !this.document)
          )
            return (e.reject(new Error("No Document Available")), n);
          if (
            (this.iframe.contentDocument.open(),
            window.MSApp && MSApp.execUnsafeLocalFunction)
          ) {
            var i = this;
            MSApp.execUnsafeLocalFunction(function () {
              i.iframe.contentDocument.write(t);
            });
          } else this.iframe.contentDocument.write(t);
          this.iframe.contentDocument.close();
        }
        return n;
      }
      onLoad(t, e) {
        ((this.window = this.iframe.contentWindow),
          (this.document = this.iframe.contentDocument),
          (this.contents = new a.a(
            this.document,
            this.document.body,
            this.section.cfiBase,
            this.section.index,
          )),
          (this.rendering = !1));
        var n = this.document.querySelector("link[rel='canonical']");
        (n
          ? n.setAttribute("href", this.section.canonical)
          : ((n = this.document.createElement("link")).setAttribute(
              "rel",
              "canonical",
            ),
            n.setAttribute("href", this.section.canonical),
            this.document.querySelector("head").appendChild(n)),
          this.contents.on(h.c.CONTENTS.EXPAND, () => {
            this.displayed &&
              this.iframe &&
              (this.expand(),
              this.contents && this.layout.format(this.contents));
          }),
          this.contents.on(h.c.CONTENTS.RESIZE, (t) => {
            this.displayed &&
              this.iframe &&
              (this.expand(),
              this.contents && this.layout.format(this.contents));
          }),
          e.resolve(this.contents));
      }
      setLayout(t) {
        ((this.layout = t),
          this.contents && (this.layout.format(this.contents), this.expand()));
      }
      setAxis(t) {
        ((this.settings.axis = t),
          (this.element.style.flex = "horizontal" == t ? "none" : "initial"),
          this.size());
      }
      setWritingMode(t) {
        this.writingMode = t;
      }
      addListeners() {}
      removeListeners(t) {}
      display(t) {
        var e = new s.defer();
        return (
          this.displayed
            ? e.resolve(this)
            : this.render(t).then(
                function () {
                  (this.emit(h.c.VIEWS.DISPLAYED, this),
                    this.onDisplayed(this),
                    (this.displayed = !0),
                    e.resolve(this));
                }.bind(this),
                function (t) {
                  e.reject(t, this);
                },
              ),
          e.promise
        );
      }
      show() {
        ((this.element.style.visibility = "visible"),
          this.iframe &&
            ((this.iframe.style.visibility = "visible"),
            (this.iframe.style.transform = "translateZ(0)"),
            this.iframe.offsetWidth,
            (this.iframe.style.transform = null)),
          this.emit(h.c.VIEWS.SHOWN, this));
      }
      hide() {
        ((this.element.style.visibility = "hidden"),
          (this.iframe.style.visibility = "hidden"),
          (this.stopExpanding = !0),
          this.emit(h.c.VIEWS.HIDDEN, this));
      }
      offset() {
        return {
          top: this.element.offsetTop,
          left: this.element.offsetLeft,
        };
      }
      width() {
        return this._width;
      }
      height() {
        return this._height;
      }
      position() {
        return this.element.getBoundingClientRect();
      }
      locationOf(t) {
        this.iframe.getBoundingClientRect();
        var e = this.contents.locationOf(t, this.settings.ignoreClass);
        return {
          left: e.left,
          top: e.top,
        };
      }
      onDisplayed(t) {}
      onResize(t, e) {}
      bounds(t) {
        return (
          (!t && this.elementBounds) ||
            (this.elementBounds = Object(s.bounds)(this.element)),
          this.elementBounds
        );
      }
      highlight(t, e = {}, n, i = "epubjs-hl", r = {}) {
        if (!this.contents) return;
        const s = Object.assign(
          {
            fill: "yellow",
            "fill-opacity": "0.3",
            "mix-blend-mode": "multiply",
          },
          r,
        );
        let o = this.contents.range(t),
          a = () => {
            this.emit(h.c.VIEWS.MARK_CLICKED, t, e);
          };
        ((e.epubcfi = t),
          this.pane || (this.pane = new l.Pane(this.iframe, this.element)));
        let u = new l.Highlight(o, i, e, s),
          c = this.pane.addMark(u);
        return (
          (this.highlights[t] = {
            mark: c,
            element: c.element,
            listeners: [a, n],
          }),
          c.element.setAttribute("ref", i),
          c.element.addEventListener("click", a),
          c.element.addEventListener("touchstart", a),
          n &&
            (c.element.addEventListener("click", n),
            c.element.addEventListener("touchstart", n)),
          c
        );
      }
      underline(t, e = {}, n, i = "epubjs-ul", r = {}) {
        if (!this.contents) return;
        const s = Object.assign(
          {
            stroke: "black",
            "stroke-opacity": "0.3",
            "mix-blend-mode": "multiply",
          },
          r,
        );
        let o = this.contents.range(t),
          a = () => {
            this.emit(h.c.VIEWS.MARK_CLICKED, t, e);
          };
        ((e.epubcfi = t),
          this.pane || (this.pane = new l.Pane(this.iframe, this.element)));
        let u = new l.Underline(o, i, e, s),
          c = this.pane.addMark(u);
        return (
          (this.underlines[t] = {
            mark: c,
            element: c.element,
            listeners: [a, n],
          }),
          c.element.setAttribute("ref", i),
          c.element.addEventListener("click", a),
          c.element.addEventListener("touchstart", a),
          n &&
            (c.element.addEventListener("click", n),
            c.element.addEventListener("touchstart", n)),
          c
        );
      }
      mark(t, e = {}, n) {
        if (!this.contents) return;
        if (t in this.marks) {
          return this.marks[t];
        }
        let i = this.contents.range(t);
        if (!i) return;
        let r = i.commonAncestorContainer,
          s = 1 === r.nodeType ? r : r.parentNode,
          o = (n) => {
            this.emit(h.c.VIEWS.MARK_CLICKED, t, e);
          };
        i.collapsed && 1 === r.nodeType
          ? ((i = new Range()), i.selectNodeContents(r))
          : i.collapsed && ((i = new Range()), i.selectNodeContents(s));
        let a = this.document.createElement("a");
        return (
          a.setAttribute("ref", "epubjs-mk"),
          (a.style.position = "absolute"),
          (a.dataset.epubcfi = t),
          e &&
            Object.keys(e).forEach((t) => {
              a.dataset[t] = e[t];
            }),
          n &&
            (a.addEventListener("click", n),
            a.addEventListener("touchstart", n)),
          a.addEventListener("click", o),
          a.addEventListener("touchstart", o),
          this.placeMark(a, i),
          this.element.appendChild(a),
          (this.marks[t] = {
            element: a,
            range: i,
            listeners: [o, n],
          }),
          s
        );
      }
      placeMark(t, e) {
        let n, i, r;
        if (
          "pre-paginated" === this.layout.name ||
          "horizontal" !== this.settings.axis
        ) {
          let t = e.getBoundingClientRect();
          ((n = t.top), (i = t.right));
        } else {
          let t,
            o = e.getClientRects();
          for (var s = 0; s != o.length; s++)
            ((t = o[s]),
              (!r || t.left < r) &&
                ((r = t.left),
                (i =
                  Math.ceil(r / this.layout.props.pageWidth) *
                    this.layout.props.pageWidth -
                  this.layout.gap / 2),
                (n = t.top)));
        }
        ((t.style.top = n + "px"), (t.style.left = i + "px"));
      }
      unhighlight(t) {
        let e;
        t in this.highlights &&
          ((e = this.highlights[t]),
          this.pane.removeMark(e.mark),
          e.listeners.forEach((t) => {
            t &&
              (e.element.removeEventListener("click", t),
              e.element.removeEventListener("touchstart", t));
          }),
          delete this.highlights[t]);
      }
      ununderline(t) {
        let e;
        t in this.underlines &&
          ((e = this.underlines[t]),
          this.pane.removeMark(e.mark),
          e.listeners.forEach((t) => {
            t &&
              (e.element.removeEventListener("click", t),
              e.element.removeEventListener("touchstart", t));
          }),
          delete this.underlines[t]);
      }
      unmark(t) {
        let e;
        t in this.marks &&
          ((e = this.marks[t]),
          this.element.removeChild(e.element),
          e.listeners.forEach((t) => {
            t &&
              (e.element.removeEventListener("click", t),
              e.element.removeEventListener("touchstart", t));
          }),
          delete this.marks[t]);
      }
      destroy() {
        for (let t in this.highlights) this.unhighlight(t);
        for (let t in this.underlines) this.ununderline(t);
        for (let t in this.marks) this.unmark(t);
        (this.blobUrl && Object(s.revokeBlobUrl)(this.blobUrl),
          this.displayed &&
            ((this.displayed = !1),
            this.removeListeners(),
            this.contents.destroy(),
            (this.stopExpanding = !0),
            this.element.removeChild(this.iframe),
            (this.iframe = void 0),
            (this.contents = void 0),
            (this._textWidth = null),
            (this._textHeight = null),
            (this._width = null),
            (this._height = null)));
      }
    }
    (r()(u.prototype), (e.a = u));
  },
  22: function (t, e, n) {
    var i = n(20),
      r = n(55),
      s = n(57),
      o = Math.max,
      a = Math.min;
    t.exports = function (t, e, n) {
      var h,
        l,
        u,
        c,
        d,
        f,
        p = 0,
        g = !1,
        m = !1,
        v = !0;
      if ("function" != typeof t) throw new TypeError("Expected a function");
      function y(e) {
        var n = h,
          i = l;
        return ((h = l = void 0), (p = e), (c = t.apply(i, n)));
      }
      function b(t) {
        return ((p = t), (d = setTimeout(x, e)), g ? y(t) : c);
      }
      function w(t) {
        var n = t - f;
        return void 0 === f || n >= e || n < 0 || (m && t - p >= u);
      }
      function x() {
        var t = r();
        if (w(t)) return _(t);
        d = setTimeout(
          x,
          (function (t) {
            var n = e - (t - f);
            return m ? a(n, u - (t - p)) : n;
          })(t),
        );
      }
      function _(t) {
        return ((d = void 0), v && h ? y(t) : ((h = l = void 0), c));
      }
      function E() {
        var t = r(),
          n = w(t);
        if (((h = arguments), (l = this), (f = t), n)) {
          if (void 0 === d) return b(f);
          if (m) return (clearTimeout(d), (d = setTimeout(x, e)), y(f));
        }
        return (void 0 === d && (d = setTimeout(x, e)), c);
      }
      return (
        (e = s(e) || 0),
        i(n) &&
          ((g = !!n.leading),
          (u = (m = "maxWait" in n) ? o(s(n.maxWait) || 0, e) : u),
          (v = "trailing" in n ? !!n.trailing : v)),
        (E.cancel = function () {
          (void 0 !== d && clearTimeout(d), (p = 0), (h = f = l = d = void 0));
        }),
        (E.flush = function () {
          return void 0 === d ? c : _(r());
        }),
        E
      );
    };
  },
  23: function (t, e, n) {
    "use strict";
    var i = n(0),
      r = n(13),
      s = n(1),
      o = n(3),
      a = n.n(o);
    const h = Math.PI / 2,
      l = {
        easeOutSine: function (t) {
          return Math.sin(t * h);
        },
        easeInOutSine: function (t) {
          return -0.5 * (Math.cos(Math.PI * t) - 1);
        },
        easeInOutQuint: function (t) {
          return (t /= 0.5) < 1
            ? 0.5 * Math.pow(t, 5)
            : 0.5 * (Math.pow(t - 2, 5) + 2);
        },
        easeInCubic: function (t) {
          return Math.pow(t, 3);
        },
      };
    class u {
      constructor(t, e) {
        ((this.settings = Object(i.extend)(
          {
            duration: 80,
            minVelocity: 0.2,
            minDistance: 10,
            easing: l.easeInCubic,
          },
          e || {},
        )),
          (this.supportsTouch = this.supportsTouch()),
          this.supportsTouch && this.setup(t));
      }
      setup(t) {
        ((this.manager = t),
          (this.layout = this.manager.layout),
          (this.fullsize = this.manager.settings.fullsize),
          this.fullsize
            ? ((this.element = this.manager.stage.element),
              (this.scroller = window),
              this.disableScroll())
            : ((this.element = this.manager.stage.container),
              (this.scroller = this.element),
              (this.element.style.WebkitOverflowScrolling = "touch")),
          (this.manager.settings.offset = this.layout.width),
          (this.manager.settings.afterScrolledTimeout =
            2 * this.settings.duration),
          (this.isVertical = "vertical" === this.manager.settings.axis),
          this.manager.isPaginated &&
            !this.isVertical &&
            ((this.touchCanceler = !1),
            (this.resizeCanceler = !1),
            (this.snapping = !1),
            this.scrollLeft,
            this.scrollTop,
            (this.startTouchX = void 0),
            (this.startTouchY = void 0),
            (this.startTime = void 0),
            (this.endTouchX = void 0),
            (this.endTouchY = void 0),
            (this.endTime = void 0),
            this.addListeners()));
      }
      supportsTouch() {
        return !!(
          "ontouchstart" in window ||
          (window.DocumentTouch && document instanceof DocumentTouch)
        );
      }
      disableScroll() {
        this.element.style.overflow = "hidden";
      }
      enableScroll() {
        this.element.style.overflow = "";
      }
      addListeners() {
        ((this._onResize = this.onResize.bind(this)),
          window.addEventListener("resize", this._onResize),
          (this._onScroll = this.onScroll.bind(this)),
          this.scroller.addEventListener("scroll", this._onScroll),
          (this._onTouchStart = this.onTouchStart.bind(this)),
          this.scroller.addEventListener("touchstart", this._onTouchStart, {
            passive: !0,
          }),
          this.on("touchstart", this._onTouchStart),
          (this._onTouchMove = this.onTouchMove.bind(this)),
          this.scroller.addEventListener("touchmove", this._onTouchMove, {
            passive: !0,
          }),
          this.on("touchmove", this._onTouchMove),
          (this._onTouchEnd = this.onTouchEnd.bind(this)),
          this.scroller.addEventListener("touchend", this._onTouchEnd, {
            passive: !0,
          }),
          this.on("touchend", this._onTouchEnd),
          (this._afterDisplayed = this.afterDisplayed.bind(this)),
          this.manager.on(s.c.MANAGERS.ADDED, this._afterDisplayed));
      }
      removeListeners() {
        (window.removeEventListener("resize", this._onResize),
          (this._onResize = void 0),
          this.scroller.removeEventListener("scroll", this._onScroll),
          (this._onScroll = void 0),
          this.scroller.removeEventListener("touchstart", this._onTouchStart, {
            passive: !0,
          }),
          this.off("touchstart", this._onTouchStart),
          (this._onTouchStart = void 0),
          this.scroller.removeEventListener("touchmove", this._onTouchMove, {
            passive: !0,
          }),
          this.off("touchmove", this._onTouchMove),
          (this._onTouchMove = void 0),
          this.scroller.removeEventListener("touchend", this._onTouchEnd, {
            passive: !0,
          }),
          this.off("touchend", this._onTouchEnd),
          (this._onTouchEnd = void 0),
          this.manager.off(s.c.MANAGERS.ADDED, this._afterDisplayed),
          (this._afterDisplayed = void 0));
      }
      afterDisplayed(t) {
        let e = t.contents;
        ["touchstart", "touchmove", "touchend"].forEach((t) => {
          e.on(t, (t) => this.triggerViewEvent(t, e));
        });
      }
      triggerViewEvent(t, e) {
        this.emit(t.type, t, e);
      }
      onScroll(t) {
        ((this.scrollLeft = this.fullsize
          ? window.scrollX
          : this.scroller.scrollLeft),
          (this.scrollTop = this.fullsize
            ? window.scrollY
            : this.scroller.scrollTop));
      }
      onResize(t) {
        this.resizeCanceler = !0;
      }
      onTouchStart(t) {
        let { screenX: e, screenY: n } = t.touches[0];
        (this.fullsize && this.enableScroll(),
          (this.touchCanceler = !0),
          this.startTouchX ||
            ((this.startTouchX = e),
            (this.startTouchY = n),
            (this.startTime = this.now())),
          (this.endTouchX = e),
          (this.endTouchY = n),
          (this.endTime = this.now()));
      }
      onTouchMove(t) {
        let { screenX: e, screenY: n } = t.touches[0],
          i = Math.abs(n - this.endTouchY);
        ((this.touchCanceler = !0),
          !this.fullsize &&
            i < 10 &&
            (this.element.scrollLeft -= e - this.endTouchX),
          (this.endTouchX = e),
          (this.endTouchY = n),
          (this.endTime = this.now()));
      }
      onTouchEnd(t) {
        (this.fullsize && this.disableScroll(), (this.touchCanceler = !1));
        let e = this.wasSwiped();
        (0 !== e ? this.snap(e) : this.snap(),
          (this.startTouchX = void 0),
          (this.startTouchY = void 0),
          (this.startTime = void 0),
          (this.endTouchX = void 0),
          (this.endTouchY = void 0),
          (this.endTime = void 0));
      }
      wasSwiped() {
        let t = this.layout.pageWidth * this.layout.divisor,
          e = this.endTouchX - this.startTouchX,
          n = Math.abs(e),
          i = e / (this.endTime - this.startTime),
          r = this.settings.minVelocity;
        return n <= this.settings.minDistance || n >= t
          ? 0
          : i > r
            ? -1
            : i < -r
              ? 1
              : void 0;
      }
      needsSnap() {
        return (
          this.scrollLeft % (this.layout.pageWidth * this.layout.divisor) != 0
        );
      }
      snap(t = 0) {
        let e = this.scrollLeft,
          n = this.layout.pageWidth * this.layout.divisor,
          i = Math.round(e / n) * n;
        return (t && (i += t * n), this.smoothScrollTo(i));
      }
      smoothScrollTo(t) {
        const e = new i.defer(),
          n = this.scrollLeft,
          r = this.now(),
          s = this.settings.duration,
          o = this.settings.easing;
        return (
          (this.snapping = !0),
          function i() {
            const a = this.now(),
              h = Math.min(1, (a - r) / s);
            if ((o(h), this.touchCanceler || this.resizeCanceler))
              return (
                (this.resizeCanceler = !1),
                (this.snapping = !1),
                void e.resolve()
              );
            h < 1
              ? (window.requestAnimationFrame(i.bind(this)),
                this.scrollTo(n + (t - n) * h, 0))
              : (this.scrollTo(t, 0), (this.snapping = !1), e.resolve());
          }.call(this),
          e.promise
        );
      }
      scrollTo(t = 0, e = 0) {
        this.fullsize
          ? window.scroll(t, e)
          : ((this.scroller.scrollLeft = t), (this.scroller.scrollTop = e));
      }
      now() {
        return "now" in window.performance
          ? performance.now()
          : new Date().getTime();
      }
      destroy() {
        this.scroller &&
          (this.fullsize && this.enableScroll(),
          this.removeListeners(),
          (this.scroller = void 0));
      }
    }
    a()(u.prototype);
    var c = u,
      d = n(22),
      f = n.n(d);
    class p extends r.a {
      constructor(t) {
        (super(t),
          (this.name = "continuous"),
          (this.settings = Object(i.extend)(this.settings || {}, {
            infinite: !0,
            overflow: void 0,
            axis: void 0,
            writingMode: void 0,
            flow: "scrolled",
            offset: 500,
            offsetDelta: 250,
            width: void 0,
            height: void 0,
            snap: !1,
            afterScrolledTimeout: 10,
          })),
          Object(i.extend)(this.settings, t.settings || {}),
          "undefined" != t.settings.gap &&
            0 === t.settings.gap &&
            (this.settings.gap = t.settings.gap),
          (this.viewSettings = {
            ignoreClass: this.settings.ignoreClass,
            axis: this.settings.axis,
            flow: this.settings.flow,
            layout: this.layout,
            width: 0,
            height: 0,
            forceEvenPages: !1,
          }),
          (this.scrollTop = 0),
          (this.scrollLeft = 0));
      }
      display(t, e) {
        return r.a.prototype.display.call(this, t, e).then(
          function () {
            return this.fill();
          }.bind(this),
        );
      }
      fill(t) {
        var e = t || new i.defer();
        return (
          this.q
            .enqueue(() => this.check())
            .then((t) => {
              t ? this.fill(e) : e.resolve();
            }),
          e.promise
        );
      }
      moveTo(t) {
        var e = 0,
          n = 0;
        (this.isPaginated
          ? ((e = Math.floor(t.left / this.layout.delta) * this.layout.delta),
            this.settings.offsetDelta)
          : ((n = t.top), t.top, this.settings.offsetDelta),
          (e > 0 || n > 0) && this.scrollBy(e, n, !0));
      }
      afterResized(t) {
        this.emit(s.c.MANAGERS.RESIZE, t.section);
      }
      removeShownListeners(t) {
        t.onDisplayed = function () {};
      }
      add(t) {
        var e = this.createView(t);
        return (
          this.views.append(e),
          e.on(s.c.VIEWS.RESIZED, (t) => {
            e.expanded = !0;
          }),
          e.on(s.c.VIEWS.AXIS, (t) => {
            this.updateAxis(t);
          }),
          e.on(s.c.VIEWS.WRITING_MODE, (t) => {
            this.updateWritingMode(t);
          }),
          (e.onDisplayed = this.afterDisplayed.bind(this)),
          (e.onResize = this.afterResized.bind(this)),
          e.display(this.request)
        );
      }
      append(t) {
        var e = this.createView(t);
        return (
          e.on(s.c.VIEWS.RESIZED, (t) => {
            e.expanded = !0;
          }),
          e.on(s.c.VIEWS.AXIS, (t) => {
            this.updateAxis(t);
          }),
          e.on(s.c.VIEWS.WRITING_MODE, (t) => {
            this.updateWritingMode(t);
          }),
          this.views.append(e),
          (e.onDisplayed = this.afterDisplayed.bind(this)),
          e
        );
      }
      prepend(t) {
        var e = this.createView(t);
        return (
          e.on(s.c.VIEWS.RESIZED, (t) => {
            (this.counter(t), (e.expanded = !0));
          }),
          e.on(s.c.VIEWS.AXIS, (t) => {
            this.updateAxis(t);
          }),
          e.on(s.c.VIEWS.WRITING_MODE, (t) => {
            this.updateWritingMode(t);
          }),
          this.views.prepend(e),
          (e.onDisplayed = this.afterDisplayed.bind(this)),
          e
        );
      }
      counter(t) {
        "vertical" === this.settings.axis
          ? this.scrollBy(0, t.heightDelta, !0)
          : this.scrollBy(t.widthDelta, 0, !0);
      }
      update(t) {
        for (
          var e,
            n = this.bounds(),
            r = this.views.all(),
            s = r.length,
            o = [],
            a = void 0 !== t ? t : this.settings.offset || 0,
            h = new i.defer(),
            l = [],
            u = 0;
          u < s;
          u++
        )
          if (((e = r[u]), !0 === this.isVisible(e, a, a, n))) {
            if (e.displayed) e.show();
            else {
              let t = e.display(this.request).then(
                function (t) {
                  t.show();
                },
                (t) => {
                  e.hide();
                },
              );
              l.push(t);
            }
            o.push(e);
          } else
            (this.q.enqueue(e.destroy.bind(e)),
              clearTimeout(this.trimTimeout),
              (this.trimTimeout = setTimeout(
                function () {
                  this.q.enqueue(this.trim.bind(this));
                }.bind(this),
                250,
              )));
        return l.length
          ? Promise.all(l).catch((t) => {
              h.reject(t);
            })
          : (h.resolve(), h.promise);
      }
      check(t, e) {
        var n = new i.defer(),
          r = [],
          s = "horizontal" === this.settings.axis,
          o = this.settings.offset || 0;
        (t && s && (o = t), e && !s && (o = e));
        var a = this._bounds;
        let h = s ? this.scrollLeft : this.scrollTop,
          l = s ? Math.floor(a.width) : a.height,
          u = s ? this.container.scrollWidth : this.container.scrollHeight,
          c =
            this.writingMode && 0 === this.writingMode.indexOf("vertical")
              ? "vertical"
              : "horizontal",
          d = this.settings.rtlScrollType,
          f = "rtl" === this.settings.direction;
        this.settings.fullsize
          ? ((s && f && "negative" === d) || (!s && f && "default" === d)) &&
            (h *= -1)
          : (f && "default" === d && "horizontal" === c && (h = u - l - h),
            f && "negative" === d && "horizontal" === c && (h *= -1));
        let p = () => {
            let t = this.views.first(),
              e = t && t.section.prev();
            e && r.push(this.prepend(e));
          },
          g = h - o;
        (h + l + o >= u &&
          (() => {
            let t = this.views.last(),
              e = t && t.section.next();
            e && r.push(this.append(e));
          })(),
          g < 0 && p());
        let m = r.map((t) => t.display(this.request));
        return r.length
          ? Promise.all(m)
              .then(() => this.check())
              .then(
                () => this.update(o),
                (t) => t,
              )
          : (this.q.enqueue(
              function () {
                this.update();
              }.bind(this),
            ),
            n.resolve(!1),
            n.promise);
      }
      trim() {
        for (
          var t = new i.defer(),
            e = this.views.displayed(),
            n = e[0],
            r = e[e.length - 1],
            s = this.views.indexOf(n),
            o = this.views.indexOf(r),
            a = this.views.slice(0, s),
            h = this.views.slice(o + 1),
            l = 0;
          l < a.length - 1;
          l++
        )
          this.erase(a[l], a);
        for (var u = 1; u < h.length; u++) this.erase(h[u]);
        return (t.resolve(), t.promise);
      }
      erase(t, e) {
        var n, i;
        this.settings.fullsize
          ? ((n = window.scrollY), (i = window.scrollX))
          : ((n = this.container.scrollTop), (i = this.container.scrollLeft));
        var r = t.bounds();
        (this.views.remove(t),
          e &&
            ("vertical" === this.settings.axis
              ? this.scrollTo(0, n - r.height, !0)
              : "rtl" === this.settings.direction
                ? this.settings.fullsize
                  ? this.scrollTo(i + Math.floor(r.width), 0, !0)
                  : this.scrollTo(i, 0, !0)
                : this.scrollTo(i - Math.floor(r.width), 0, !0)));
      }
      addEventListeners(t) {
        ((this._onPageHide = function () {
          ((this.ignore = !0), this.destroy());
        }.bind(this)),
          window.addEventListener("pagehide", this._onPageHide),
          this.addScrollListeners(),
          this.isPaginated &&
            this.settings.snap &&
            (this.snapper = new c(
              this,
              this.settings.snap &&
                "object" == typeof this.settings.snap &&
                this.settings.snap,
            )));
      }
      addScrollListeners() {
        var t;
        this.tick = i.requestAnimationFrame;
        let e =
          "rtl" === this.settings.direction &&
          "default" === this.settings.rtlScrollType
            ? -1
            : 1;
        ((this.scrollDeltaVert = 0),
          (this.scrollDeltaHorz = 0),
          this.settings.fullsize
            ? ((t = window),
              (this.scrollTop = window.scrollY * e),
              (this.scrollLeft = window.scrollX * e))
            : ((t = this.container),
              (this.scrollTop = this.container.scrollTop),
              (this.scrollLeft = this.container.scrollLeft)),
          (this._onScroll = this.onScroll.bind(this)),
          t.addEventListener("scroll", this._onScroll),
          (this._scrolled = f()(this.scrolled.bind(this), 30)),
          (this.didScroll = !1));
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
      onScroll() {
        let t,
          e,
          n =
            "rtl" === this.settings.direction &&
            "default" === this.settings.rtlScrollType
              ? -1
              : 1;
        (this.settings.fullsize
          ? ((t = window.scrollY * n), (e = window.scrollX * n))
          : ((t = this.container.scrollTop), (e = this.container.scrollLeft)),
          (this.scrollTop = t),
          (this.scrollLeft = e),
          this.ignore ? (this.ignore = !1) : this._scrolled(),
          (this.scrollDeltaVert += Math.abs(t - this.prevScrollTop)),
          (this.scrollDeltaHorz += Math.abs(e - this.prevScrollLeft)),
          (this.prevScrollTop = t),
          (this.prevScrollLeft = e),
          clearTimeout(this.scrollTimeout),
          (this.scrollTimeout = setTimeout(
            function () {
              ((this.scrollDeltaVert = 0), (this.scrollDeltaHorz = 0));
            }.bind(this),
            150,
          )),
          clearTimeout(this.afterScrolled),
          (this.didScroll = !1));
      }
      scrolled() {
        (this.q.enqueue(
          function () {
            return this.check();
          }.bind(this),
        ),
          this.emit(s.c.MANAGERS.SCROLL, {
            top: this.scrollTop,
            left: this.scrollLeft,
          }),
          clearTimeout(this.afterScrolled),
          (this.afterScrolled = setTimeout(
            function () {
              (this.snapper &&
                this.snapper.supportsTouch &&
                this.snapper.needsSnap()) ||
                this.emit(s.c.MANAGERS.SCROLLED, {
                  top: this.scrollTop,
                  left: this.scrollLeft,
                });
            }.bind(this),
            this.settings.afterScrolledTimeout,
          )));
      }
      next() {
        let t =
          "pre-paginated" === this.layout.props.name && this.layout.props.spread
            ? 2 * this.layout.props.delta
            : this.layout.props.delta;
        this.views.length &&
          (this.isPaginated && "horizontal" === this.settings.axis
            ? this.scrollBy(t, 0, !0)
            : this.scrollBy(0, this.layout.height, !0),
          this.q.enqueue(
            function () {
              return this.check();
            }.bind(this),
          ));
      }
      prev() {
        let t =
          "pre-paginated" === this.layout.props.name && this.layout.props.spread
            ? 2 * this.layout.props.delta
            : this.layout.props.delta;
        this.views.length &&
          (this.isPaginated && "horizontal" === this.settings.axis
            ? this.scrollBy(-t, 0, !0)
            : this.scrollBy(0, -this.layout.height, !0),
          this.q.enqueue(
            function () {
              return this.check();
            }.bind(this),
          ));
      }
      updateFlow(t) {
        (this.rendered &&
          this.snapper &&
          (this.snapper.destroy(), (this.snapper = void 0)),
          super.updateFlow(t, "scroll"),
          this.rendered &&
            this.isPaginated &&
            this.settings.snap &&
            (this.snapper = new c(
              this,
              this.settings.snap &&
                "object" == typeof this.settings.snap &&
                this.settings.snap,
            )));
      }
      destroy() {
        (super.destroy(), this.snapper && this.snapper.destroy());
      }
    }
    e.a = p;
  },
};
