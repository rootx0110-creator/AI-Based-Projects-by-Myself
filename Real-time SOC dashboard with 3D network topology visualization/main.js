const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');

ipcMain.handle('save-report-html', async (event, html, suggestedName) => {
  const { canceled, filePath } = await dialog.showSaveDialog({
    title: 'Save SOC Report',
    defaultPath: path.join(app.getPath('documents'), suggestedName),
    filters: [{ name: 'HTML Report', extensions: ['html'] }]
  });
  if (canceled || !filePath) return { canceled: true };
  await fs.promises.writeFile(filePath, html, 'utf-8');
  return { canceled: false, filePath };
});

function createWindow() {
  const win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    backgroundColor: '#070b16',
    title: 'SOC 3D Dashboard',
    autoHideMenuBar: true,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  });

  win.once('ready-to-show', () => win.show());
  win.loadFile(path.join(__dirname, 'renderer', 'index.html'));
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});