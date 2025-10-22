from interfaces.main_window import BluetoothProgramApp

if __name__ == "__main__":
    app = BluetoothProgramApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
