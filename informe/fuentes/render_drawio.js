// Exporta archivos .drawio a PNG con el visor oficial de draw.io (viewer-static.min.js)
// en Chromium sin ventana (Playwright).
//   VISOR=/ruta/viewer-static.min.js node render_drawio.js a.drawio a.png [b.drawio b.png ...]
// En la práctica las figuras se pueden abrir y exportar también desde draw.io.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const visor = process.env.VISOR;
  const html = path.join(path.dirname(visor), 'visor_blanco.html');
  fs.writeFileSync(html, '<!DOCTYPE html><html><head><meta charset="utf-8"></head>' +
    '<body style="margin:0;background:#fff"><div id="g"></div>' +
    `<script src="file://${visor}"></script></body></html>`);
  const browser = await chromium.launch();
  const args = process.argv.slice(2);
  for (let i = 0; i + 1 < args.length; i += 2) {
    const page = await browser.newPage({ deviceScaleFactor: 3, viewport: { width: 2000, height: 2000 } });
    await page.goto('file://' + html);
    await page.waitForFunction(() => typeof GraphViewer !== 'undefined');
    const xml = fs.readFileSync(args[i], 'utf8');
    const ok = await page.evaluate((xml) => {
      const g = document.getElementById('g');
      const doc = mxUtils.parseXml(xml);
      new GraphViewer(g, doc.documentElement, { border: 6, toolbar: null, nav: false, lightbox: false, resize: false });
      return !!g.querySelector('svg');
    }, xml);
    if (!ok) { console.log('ERROR', args[i]); continue; }
    await page.waitForTimeout(150);
    const el = await page.$('#g svg');
    await el.screenshot({ path: args[i + 1] });
    await page.close();
    console.log('PNG', path.basename(args[i + 1]));
  }
  await browser.close();
})();
