import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

function readProjectFile(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), "utf8");
}

test("global layout defines safe-area variables and prevents page-level scroll", () => {
  const resetCss = readProjectFile("static/css/base/reset.css");
  assert.match(resetCss, /--safe-area-top:/);
  assert.match(resetCss, /--safe-area-right:/);
  assert.match(resetCss, /--safe-area-bottom:/);
  assert.match(resetCss, /--safe-area-left:/);
  assert.match(resetCss, /overflow:\s*hidden;/);
  assert.match(resetCss, /overscroll-behavior:\s*none;/);
});

test("reduced-motion mode is respected", () => {
  const resetCss = readProjectFile("static/css/base/reset.css");
  assert.match(resetCss, /@media\s*\(prefers-reduced-motion:\s*reduce\)/);
  assert.match(resetCss, /transition-duration:\s*0\.01ms\s*!important;/);
});

test("reader layout contains multi-breakpoint responsive strategy", () => {
  const readerCss = readProjectFile("static/css/components/reader-layout.css");
  assert.match(readerCss, /@media\s*\(max-width:\s*1200px\)/);
  assert.match(readerCss, /@media\s*\(max-width:\s*1024px\)/);
  assert.match(readerCss, /@media\s*\(max-width:\s*900px\)/);
  assert.match(readerCss, /@media\s*\(max-width:\s*720px\)/);
  assert.match(readerCss, /@media\s*\(max-width:\s*560px\)/);
  assert.match(readerCss, /@media\s*\(max-height:\s*760px\)/);
  assert.match(readerCss, /@media\s*\(max-height:\s*620px\)/);
  assert.match(readerCss, /@media\s*\(orientation:\s*landscape\)\s*and\s*\(max-height:\s*500px\)/);
  assert.match(
    readerCss,
    /\.epub-reader-container\.immersive-reading\s*\{[\s\S]*padding:\s*calc\(var\(--safe-area-top\)\s*\+\s*8px\)/
  );
  assert.match(
    readerCss,
    /\.epub-reader-container\.immersive-reading[\s\S]*\.wrapper-main\s*\{[\s\S]*padding:\s*8px;/
  );
});

test("small-screen reader keeps side-by-side layout with compact nav controls", () => {
  const readerCss = readProjectFile("static/css/components/reader-layout.css");
  assert.match(readerCss, /@media\s*\(max-width:\s*700px\)[\s\S]*\.epub-reader-container \.epub-contents\s*\{[\s\S]*position:\s*relative;/);
  assert.match(readerCss, /@media\s*\(max-width:\s*700px\)[\s\S]*\.epub-reader-container \.epub-contents\s*\{[\s\S]*flex:\s*0 0 44%;/);
  assert.match(readerCss, /@media\s*\(max-width:\s*700px\)[\s\S]*\.epub-reader-container \.reader-wrapper\s*\{[\s\S]*flex-basis:\s*56%;/);
  assert.match(readerCss, /wrapper-main\s*\{[\s\S]*padding:\s*8px;/);
  assert.match(readerCss, /reader-wrapper-container > \[id\^="epubjs-container-"\][\s\S]*padding:\s*8px;/);
  assert.match(readerCss, /@media\s*\(max-width:\s*560px\)[\s\S]*wrapper-main\s*\{[\s\S]*padding:\s*6px;/);
  assert.match(
    readerCss,
    /@media\s*\(max-width:\s*560px\)[\s\S]*reader-wrapper-container > \[id\^="epubjs-container-"\][\s\S]*padding:\s*6px;/
  );
  assert.match(readerCss, /reader-wrapper-container > \[id\^="epubjs-container-"\][\s\S]*width:\s*100%\s*!important;/);
  assert.match(readerCss, /reader-wrapper-container > \[id\^="epubjs-container-"\][\s\S]*overflow-y:\s*auto\s*!important;/);
  assert.match(readerCss, /reader-wrapper-container > \[id\^="epubjs-container-"\] > iframe[\s\S]*width:\s*calc\(100%\s*-\s*12px\)\s*!important;/);
  assert.match(
    readerCss,
    /\.epub-contents:not\(\.close\) \+ \.reader-wrapper \.wrapper-nav \.icon-wrap-first-two\s*\{[\s\S]*justify-content:\s*flex-end;/
  );
  assert.match(
    readerCss,
    /\.epub-contents:not\(\.close\) \+ \.reader-wrapper \.wrapper-nav \.icon-anchor,\s*[\s\S]*\.reader-nav-right\s*\{[\s\S]*display:\s*none\s*!important;/
  );
  assert.match(
    readerCss,
    /\.epub-contents:not\(\.close\) \+ \.reader-wrapper \.wrapper-main\s*\{[\s\S]*pointer-events:\s*none;/
  );
  assert.match(
    readerCss,
    /\.epub-contents:not\(\.close\) \+ \.reader-wrapper \.wrapper-nav\s*\{[\s\S]*justify-content:\s*flex-end;[\s\S]*overflow:\s*hidden;/
  );
  assert.match(
    readerCss,
    /@media\s*\(max-width:\s*720px\)[\s\S]*\.wrapper-nav\s*\{[\s\S]*padding:\s*0 10px;/
  );
  assert.match(
    readerCss,
    /\.epub-reader-container \.epub-contents:not\(\.close\)\s*\{[\s\S]*flex:\s*1 1 auto;/
  );
  assert.match(
    readerCss,
    /\.epub-reader-container \.epub-contents:not\(\.close\) \+ \.reader-wrapper\s*\{[\s\S]*flex:\s*0 0 56px;[\s\S]*min-width:\s*56px;/
  );
  assert.doesNotMatch(readerCss, /transform:\s*translateX\(calc\(-100%\s*-\s*14px\)\);/);
});

test("landing page keeps safe-area spacing at desktop and mobile sizes", () => {
  const landingCss = readProjectFile("static/css/components/landing-screen.css");
  assert.match(landingCss, /padding:\s*calc\(24px \+ var\(--safe-area-top\)\)/);
  assert.match(landingCss, /@media\s*\(max-width:\s*640px\)/);
  assert.match(landingCss, /@media\s*\(max-width:\s*480px\)/);
  assert.match(landingCss, /max-height:\s*min\(780px,\s*calc\(100dvh/);
  assert.match(landingCss, /overflow:\s*auto;/);
  assert.match(landingCss, /@media\s*\(max-height:\s*720px\)/);
  assert.match(landingCss, /@media\s*\(orientation:\s*landscape\)\s*and\s*\(max-height:\s*500px\)/);
});
