import test from "node:test";
import assert from "node:assert/strict";
import { typescriptModule } from "./typescript-module.mjs";
const { paginationItems, paginationURL } = await typescriptModule(new URL("../../../app/web/src/lib/pagination.ts", import.meta.url));

test("short page ranges show every number, including the current page and both boundaries", () => {
  assert.deepEqual(paginationItems(1,1),[1]);
  assert.deepEqual(paginationItems(2,6),[1,2,3,4,5,6]);
  assert.deepEqual(paginationItems(1,0),[]);
  assert.deepEqual(paginationItems(11,10),[]);
});

test("long ranges use bounded windows and never replace one missing page with an ellipsis", () => {
  assert.deepEqual(paginationItems(4,100),[1,2,3,4,5,"gap-after",100]);
  assert.deepEqual(paginationItems(50,100),[1,"gap-before",49,50,51,"gap-after",100]);
  assert.deepEqual(paginationItems(99,100),[1,"gap-before",96,97,98,99,100]);
  for(const slots of [5,7]) for(let total=1;total<=100;total++) for(let page=1;page<=total;page++) {
    const items=paginationItems(page,total,slots), numbers=items.filter(item=>typeof item==="number");
    assert.ok(items.length<=slots); assert.ok(numbers.includes(page));
    assert.equal(numbers[0],1); assert.equal(numbers.at(-1),total);
    assert.deepEqual(numbers,[...new Set(numbers)].sort((a,b)=>a-b));
    for(let index=1;index<items.length-1;index++) if(typeof items[index]==="string") assert.ok(items[index+1]-items[index-1]>2);
  }
});

test("phone windows stay compact while preserving the real first, current and last page", () => {
  assert.deepEqual(paginationItems(50,100,5),[1,"gap-before",50,"gap-after",100]);
  assert.deepEqual(paginationItems(2,100,5),[1,2,3,"gap-after",100]);
});

test("jumping pages preserves filters, page size and sort and drops obsolete cursors", () => {
  const value=paginationURL(9,{pathname:"/manage/books/",query:"q=বাংলা&status=published&sort=-created_at&limit=50&page=2&cursor=old"});
  const url=new URL(value,"https://library.example.test");
  assert.equal(url.pathname,"/manage/books/"); assert.equal(url.searchParams.get("q"),"বাংলা");
  assert.equal(url.searchParams.get("status"),"published"); assert.equal(url.searchParams.get("sort"),"-created_at");
  assert.equal(url.searchParams.get("limit"),"50"); assert.equal(url.searchParams.get("page"),"9");
  assert.equal(url.searchParams.has("cursor"),false);
});
