import { archiveText, localPath, type LocalPackage } from "./package";

export class LocalBookResources {
  private urls = new Map<string, string>();
  constructor(private files: Map<string, Uint8Array>, readonly book: LocalPackage) {
    for (const item of book.items.filter(item => /^(?:image|font)\//.test(item.type) || ["application/font-woff", "application/vnd.ms-opentype"].includes(item.type))) {
      this.urls.set(item.path, URL.createObjectURL(new Blob([new Uint8Array(files.get(item.path)!).buffer], { type: item.type })));
    }
    for (const item of book.items.filter(item => item.type === "text/css")) {
      this.urls.set(item.path, URL.createObjectURL(new Blob([this.styles(archiveText(files, item.path), item.path)], { type: "text/css" })));
    }
  }

  private resource(value: string, base: string) {
    if (/^data:image\/(?:png|jpeg|gif|webp);base64,/i.test(value)) return value;
    const path = localPath(value, base)?.path;
    return path ? this.urls.get(path) ?? "" : "";
  }

  private styles(value: string, base: string) {
    return value.replace(/@import\s+(?:url\([^)]*\)|[^;]*);?/gi, "").replace(/url\(\s*(['"]?)(.*?)\1\s*\)/gi, (_, _quote, path: string) => `url("${this.resource(path, base)}")`);
  }

  chapter(index: number) {
    const item = this.book.chapters[index];
    if (!item) throw new Error("invalid_epub");
    const source = archiveText(this.files, item.path);
    if (/<!ENTITY/i.test(source)) throw new Error("invalid_epub");
    const document = new DOMParser().parseFromString(source, "text/html");
    document.querySelectorAll("script,iframe,object,embed,form,input,button,textarea,select,base,meta,foreignObject,audio,video,source").forEach(element => element.remove());
    for (const element of document.querySelectorAll("*")) {
      for (const attribute of Array.from(element.attributes)) {
        if (/^on/i.test(attribute.name) || ["srcset", "ping", "action", "formaction", "target", "download", "srcdoc"].includes(attribute.name)) element.removeAttribute(attribute.name);
      }
      if (element.hasAttribute("style")) element.setAttribute("style", this.styles(element.getAttribute("style")!, item.path));
      if (element.hasAttribute("src")) element.setAttribute("src", this.resource(element.getAttribute("src")!, item.path));
      if (element.hasAttribute("xlink:href")) element.removeAttribute("xlink:href");
    }
    for (const element of document.querySelectorAll("style")) element.textContent = this.styles(element.textContent ?? "", item.path);
    for (const link of document.querySelectorAll("link")) {
      const url = this.resource(link.getAttribute("href") ?? "", item.path);
      if (link.getAttribute("rel") !== "stylesheet" || !url) link.remove(); else link.setAttribute("href", url);
    }
    for (const anchor of document.querySelectorAll("a[href]")) {
      const resolved = localPath(anchor.getAttribute("href")!, item.path);
      const chapter = this.book.chapters.findIndex(entry => entry.path === resolved?.path);
      anchor.removeAttribute("href");
      if (chapter >= 0) { anchor.setAttribute("href", `#${encodeURIComponent(resolved!.fragment)}`); anchor.setAttribute("data-local-chapter", String(chapter)); }
    }
    const policy = document.createElement("meta");
    policy.httpEquiv = "Content-Security-Policy";
    policy.content = "default-src 'none'; img-src blob: data:; style-src 'unsafe-inline' blob:; font-src blob: data:; base-uri 'none'; form-action 'none'";
    document.head.prepend(policy);
    return "<!doctype html>" + document.documentElement.outerHTML;
  }

  dispose() { for (const url of this.urls.values()) URL.revokeObjectURL(url); this.urls.clear(); this.files.clear(); }
}
