const { app, BrowserWindow, ipcMain } = require("electron");
const axios = require("axios");

let mainWindow;

app.whenReady().then(() => {
    mainWindow = new BrowserWindow({
        width: 800,
        height: 600,
        webPreferences: {
            nodeIntegration: true,
        }
    });
    mainWindow.loadFile("index.html");
});

ipcMain.handle("get-status", async () => {
    const response = await axios.get("http://127.0.0.1:8000/");
    return response.data;
});

app.on("window-all-closed", () => {
    if (process.platform !== "darwin") app.quit();
});
