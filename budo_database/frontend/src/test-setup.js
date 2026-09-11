// jsdom 30 implements CSS.escape() as a Web IDL operation whose generated
// wrapper validates its receiver. css.escape (used by jest-dom) exports an
// existing native implementation as a bare function, so bind it before the
// matcher package is evaluated.
if (window.CSS?.escape) {
  window.CSS.escape = window.CSS.escape.bind(window.CSS);
}

await import('@testing-library/jest-dom/vitest');

window.matchMedia ||= query => ({
  matches: false,
  media: query,
  addEventListener() {},
  removeEventListener() {},
});
