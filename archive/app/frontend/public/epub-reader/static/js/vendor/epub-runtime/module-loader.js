/**
 * Initializes the split EPUB runtime module table and exposes `window.ePub`.
 */
export function initializeEpubRuntime(moduleTable) {
  const modules = moduleTable || {};
  const cache = {};

  function __webpack_require__(moduleId) {
    if (cache[moduleId]) {
      return cache[moduleId].exports;
    }

    if (!Object.prototype.hasOwnProperty.call(modules, moduleId)) {
      throw new Error(`Cannot find EPUB runtime module: ${moduleId}`);
    }

    const module = (cache[moduleId] = {
      i: moduleId,
      l: false,
      exports: {}
    });

    modules[moduleId].call(module.exports, module, module.exports, __webpack_require__);
    module.l = true;

    return module.exports;
  }

  __webpack_require__.m = modules;
  __webpack_require__.c = cache;

  __webpack_require__.d = function defineExport(exportsObject, exportName, getter) {
    if (!__webpack_require__.o(exportsObject, exportName)) {
      Object.defineProperty(exportsObject, exportName, {
        enumerable: true,
        get: getter
      });
    }
  };

  __webpack_require__.r = function markAsModule(exportsObject) {
    if (typeof Symbol !== "undefined" && Symbol.toStringTag) {
      Object.defineProperty(exportsObject, Symbol.toStringTag, {
        value: "Module"
      });
    }
    Object.defineProperty(exportsObject, "__esModule", {
      value: true
    });
  };

  __webpack_require__.t = function createNamespaceObject(value, mode) {
    if (mode & 1) {
      value = __webpack_require__(value);
    }

    if (mode & 8) {
      return value;
    }

    if (mode & 4 && typeof value === "object" && value && value.__esModule) {
      return value;
    }

    const namespace = Object.create(null);
    __webpack_require__.r(namespace);

    Object.defineProperty(namespace, "default", {
      enumerable: true,
      value
    });

    if (mode & 2 && typeof value !== "string") {
      for (const key in value) {
        __webpack_require__.d(namespace, key, function getter(k) {
          return value[k];
        }.bind(null, key));
      }
    }

    return namespace;
  };

  __webpack_require__.n = function getDefaultExport(moduleObject) {
    const getter =
      moduleObject && moduleObject.__esModule
        ? function getDefault() {
            return moduleObject.default;
          }
        : function getModuleExports() {
            return moduleObject;
          };

    __webpack_require__.d(getter, "a", getter);

    return getter;
  };

  __webpack_require__.o = function hasOwnProperty(target, property) {
    return Object.prototype.hasOwnProperty.call(target, property);
  };

  __webpack_require__.p = "/";

  const entryModule = __webpack_require__(32);
  const epubApi = entryModule && (entryModule.a || entryModule.default || entryModule);

  if (typeof window !== "undefined" && epubApi) {
    window.ePub = epubApi;
  }

  return epubApi;
}
