const { build } = require('esbuild');
const path = require('path');
const fs = require('fs');

const root = path.join(__dirname, '..');
const lib = path.join(root, 'src', 'lib');

async function main() {
  fs.mkdirSync(lib, { recursive: true });

  await build({
    entryPoints: [path.join(root, 'src', 'app.js')],
    bundle: true,
    format: 'esm',
    minify: true,
    target: ['chrome120'],
    outfile: path.join(root, 'src', 'app.bundle.js'),
    logLevel: 'warning'
  });

  const check = fs.existsSync(path.join(root, 'src', 'app.bundle.js'));
  if (!check) throw new Error('app bundle missing after build');
  console.log('bundle ok', check, fs.statSync(path.join(root, 'src', 'app.bundle.js')).size);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});