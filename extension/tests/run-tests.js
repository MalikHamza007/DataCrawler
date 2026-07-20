const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = path.resolve(__dirname, "..");

function read(relative) {
  return fs.readFileSync(path.join(root, relative), "utf8");
}

function runScript(context, relative) {
  vm.runInNewContext(read(relative), context, { filename: relative });
}

function manifestTests() {
  const manifest = JSON.parse(read("manifest.json"));
  assert.equal(manifest.manifest_version, 3);
  assert.deepEqual(manifest.permissions.sort(), ["activeTab", "scripting", "storage"].sort());
  assert(!manifest.permissions.includes("<all_urls>"));
  assert(!manifest.permissions.includes("tabs"));
  assert(!manifest.permissions.includes("cookies"));
  assert(!manifest.permissions.includes("history"));
  assert(!manifest.permissions.includes("webRequest"));
  assert.deepEqual(manifest.host_permissions.sort(), ["http://127.0.0.1:8000/*", "http://localhost:8000/*"].sort());
  assert(!manifest.content_scripts);
}

function baseContext(url = "https://example.com") {
  const elements = [];
  const document = {
    title: "Example Developers",
    body: { innerText: "Example Developers Lahore 0300 1234567 sales@example.com" },
    querySelector(selector) {
      if (selector.includes("canonical")) return { href: url };
      if (selector.includes("og:title")) return { getAttribute: () => "Example Developers" };
      if (selector.includes("og:description")) return { getAttribute: () => "Public developer in Lahore" };
      return null;
    },
    querySelectorAll(selector) {
      if (selector.includes("a[href]")) return elements.filter((item) => item.tagName === "A");
      if (selector.includes("h1")) return elements.filter((item) => ["H1", "H2", "H3", "P", "LI", "ADDRESS", "MAIN", "ARTICLE", "SECTION"].includes(item.tagName));
      return [];
    }
  };
  const context = {
    window: {},
    document,
    location: new URL(url),
    URL,
    Node: { ELEMENT_NODE: 1 },
    console,
    getComputedStyle(element) {
      return element.style || { display: "block", visibility: "visible", opacity: "1" };
    }
  };
  context.window = context;
  context.__elements = elements;
  return context;
}

function element(tagName, text, attrs = {}) {
  return {
    tagName,
    nodeType: 1,
    isConnected: attrs.isConnected !== false,
    innerText: text,
    textContent: text,
    href: attrs.href,
    style: attrs.style || { display: "block", visibility: "visible", opacity: "1" },
    closest(selector) {
      return selector === "[aria-hidden='true']" && attrs.ariaHidden ? this : null;
    },
    getClientRects() {
      return attrs.zeroSize ? [] : [{}];
    }
  };
}

function loadExtractors(context) {
  ["extractors/common.js", "extractors/normalizers.js", "extractors/platform-detector.js", "extractors/generic.js", "extractors/facebook.js", "extractors/instagram.js", "extractors/x.js", "extractors/linkedin.js", "extractors/meta-ad-library.js"].forEach((file) => runScript(context, file));
}

function platformTests() {
  const context = baseContext("https://www.facebook.com/ads/library/?id=1");
  loadExtractors(context);
  assert.equal(context.window.AlduorExtractors.detectPlatform("https://www.facebook.com/example").platform, "facebook");
  assert.equal(context.window.AlduorExtractors.detectPlatform("https://www.facebook.com/ads/library/?id=1").platform, "meta_ad_library");
  assert.equal(context.window.AlduorExtractors.detectPlatform("https://www.instagram.com/example").platform, "instagram");
  assert.equal(context.window.AlduorExtractors.detectPlatform("https://x.com/example").platform, "x");
  assert.equal(context.window.AlduorExtractors.detectPlatform("https://twitter.com/example").platform, "x");
  assert.equal(context.window.AlduorExtractors.detectPlatform("https://www.linkedin.com/company/example").platform, "linkedin");
  assert.equal(context.window.AlduorExtractors.detectPlatform("https://example.com").platform, "generic");
  assert.equal(context.window.AlduorExtractors.detectPlatform("chrome://extensions").platform, "unsupported");
}

function genericExtractionTests() {
  const context = baseContext("https://example.com/projects");
  context.__elements.push(
    element("H1", "Example Developers"),
    element("P", "Call 0300 1234567 or sales@example.com for Pearl Heights on Main Boulevard Gulberg Lahore."),
    element("P", "Hidden 0300 0000000", { style: { display: "none", visibility: "visible", opacity: "1" } }),
    element("A", "WhatsApp", { href: "https://wa.me/923001234567" }),
    element("A", "Website", { href: "https://developer.example.com" }),
    element("P", "Below fold visible text", { zeroSize: false })
  );
  loadExtractors(context);
  const capture = context.window.AlduorExtractors.extractGeneric();
  assert.equal(capture.profile_name, "Example Developers");
  assert(capture.phones.some((phone) => phone.value.includes("0300 1234567")));
  assert(!capture.phones.some((phone) => phone.value.includes("0000000")));
  assert(capture.emails.some((email) => email.value === "sales@example.com"));
  assert(capture.whatsapp.length === 1);
  assert(capture.websites.includes("https://developer.example.com/"));
  assert(capture.addresses.length > 0);
  assert(capture.project_names.includes("Pearl Heights"));
  assert(capture.visible_text_excerpt.length <= 20000);
}

function visibilityTests() {
  const context = baseContext();
  loadExtractors(context);
  const A = context.window.AlduorExtractors;
  assert.equal(A.isVisible(element("P", "ok")), true);
  assert.equal(A.isVisible(element("P", "hidden", { style: { display: "none", visibility: "visible", opacity: "1" } })), false);
  assert.equal(A.isVisible(element("P", "hidden", { style: { display: "block", visibility: "hidden", opacity: "1" } })), false);
  assert.equal(A.isVisible(element("P", "hidden", { ariaHidden: true })), false);
  assert.equal(A.isVisible(element("P", "hidden", { zeroSize: true })), false);
  assert.equal(A.isVisible(element("P", "detached", { isConnected: false })), false);
}

function securityTests() {
  const allJs = fs.readdirSync(root, { recursive: true })
    .filter((file) => file.endsWith(".js"))
    .filter((file) => file !== "tests/run-tests.js")
    .map((file) => [file, read(file)]);
  for (const [file, code] of allJs) {
    assert(!/\beval\s*\(/.test(code), `${file} uses eval`);
    assert(!/new Function/.test(code), `${file} uses new Function`);
    assert(!/document\.cookie/.test(code), `${file} reads cookies`);
    assert(!/webRequest|downloads|history|bookmarks|management|identity/.test(code), `${file} references blocked API`);
    assert(!/\.scroll|scrollTo|scrollIntoView/.test(code), `${file} scrolls`);
    assert(!/innerHTML\s*=/.test(code), `${file} assigns innerHTML`);
  }
  assert(!/<script[^>]+https?:\/\//i.test(read("popup/popup.html")));
  assert(!/<script[^>]+https?:\/\//i.test(read("settings/settings.html")));
}

manifestTests();
platformTests();
genericExtractionTests();
visibilityTests();
securityTests();
console.log("Extension tests passed");
