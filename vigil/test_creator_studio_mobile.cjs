'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const html = fs.readFileSync('creator-studio-mobile.html', 'utf8');
const index = fs.readFileSync('index.html', 'utf8');

assert.match(html, /<meta name="viewport" content="width=device-width,initial-scale=1/);
assert.match(html, /id="media-status"/);
assert.match(html, /id="generate-image"/);
assert.match(html, /id="generate-video"/);
assert.ok(html.includes('/api/creator/videos'));
assert.match(html, /id="operator-login-form"/);
assert.ok(html.includes('/api/creator/status'));
assert.doesNotMatch(html, /Image generation will be connected in a later phase/);
assert.match(html, /localStorage/);
assert.match(html, /min="18"/);
assert.match(html, /id="char-consent"/);
assert.match(html, /id="adult-confirm"/);
assert.match(html, /CORELESS HOME/);
assert.match(index, /href="creator-studio-mobile\.html"[^>]*>AI CREATOR<\/a>/);

const inlineScripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)]
  .map(match => match[1])
  .filter(script => script.trim().length > 0);

assert.equal(inlineScripts.length, 1, 'mobile studio should have one inline application script');
for (const script of inlineScripts) new vm.Script(script, { filename: 'creator-studio-mobile.inline.js' });

assert.doesNotMatch(html, /<script[^>]+src=["']https?:\/\//i, 'mobile page must not load remote executable scripts');
console.log('Creator Studio mobile interface, adult-character guardrails, local library, navigation link, and inline JavaScript syntax passed.');
