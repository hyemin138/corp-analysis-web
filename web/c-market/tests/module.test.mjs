import {test} from 'node:test';
import assert from 'node:assert/strict';
import {relative,change} from '../src/domain.ts';
test('relative series keeps zero denominator unavailable',()=>{
 assert.deepEqual(relative([{date:'2026-05-11',value:0},{date:'2026-05-12',value:4}]).map(x=>x.value),[null,null]);
});
test('missing values are never replaced by zero',()=>{
 assert.equal(change(null,100),null);
 assert.equal(change(100,0),null);
 assert.ok(Math.abs(change(110,100)-10)<1e-10);
});
