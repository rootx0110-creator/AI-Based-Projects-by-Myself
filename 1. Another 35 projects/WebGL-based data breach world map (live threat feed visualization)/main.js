const { app, BrowserWindow, ipcMain, dialog, session } = require('electron');
const path = require('path');
const fs = require('fs');

const isDev = !app.isPackaged;

function createWindow() {
  const win = new BrowserWindow({
    width: 1500,
    height: 940,
    minWidth: 1024,
    minHeight: 680,
    show: false,
    backgroundColor: '#04060f',
    title: 'BreachMap - WebGL Data Breach World Map',
    icon: path.join(__dirname, 'build', 'icon.ico'),
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
      spellcheck: false
    }
  });

  win.once('ready-to-show', () => win.show());
  win.on('closed', () => null);

  win.webContents.on('console-message', (ev) => {
    if (isDev) console.log(`[renderer:${ev.lineNumber}] ${ev.message}`);
  });

  win.loadFile(path.join(__dirname, 'src', 'index.html'));
}

app.whenReady().then(() => {
  if (isDev) {
    session.defaultSession.setPermissionRequestHandler((_wc, _permission, cb) => cb(true));
  }
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

ipcMain.handle('dialog:saveTextFile', async (_event, { defaultName, content }) => {
  const win = BrowserWindow.getAllWindows()[0];
  const result = await dialog.showSaveDialog(win, {
    title: 'Save report',
    defaultPath: path.join(app.getPath('downloads'), defaultName),
    filters: [
      { name: 'HTML Report', extensions: ['html'] },
      { name: 'JSON data', extensions: ['json'] }
    ]
  });
  if (result.canceled || !result.filePath) return { canceled: true };
  try {
    fs.writeFileSync(result.filePath, content, 'utf8');
    return { canceled: false, path: result.filePath };
  } catch (err) {
    return { canceled: false, error: err.message };
  }
});

ipcMain.handle('app:version', () => app.getVersion());