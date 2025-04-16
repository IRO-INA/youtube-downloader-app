import os
import threading
import time
import requests
from io import BytesIO
from PIL import Image, ImageTk
from pytube import Playlist, YouTube
from pytube.exceptions import RegexMatchError, VideoUnavailable
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

class YouTubeDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎵 YouTube Playlist Downloader")
        self.root.geometry("850x600")
        self.root.resizable(False, False)

        self.video_vars = []
        self.video_thumbnails = []
        self.stop_download = False
        self.theme = "light"

        self.setup_gui()

    def setup_gui(self):
        # Estilos
        self.bg_light = "#f0f0f0"
        self.fg_light = "#000000"
        self.bg_dark = "#2b2b2b"
        self.fg_dark = "#ffffff"
        self.root.configure(bg=self.bg_light)

        # Tema
        self.theme_button = tk.Button(self.root, text="🌙 Modo Oscuro", command=self.toggle_theme)
        self.theme_button.pack(pady=5)

        # URL de la playlist
        tk.Label(self.root, text="URL de la Playlist:", bg=self.root['bg']).pack()
        self.url_entry = tk.Entry(self.root, width=80)
        self.url_entry.pack(pady=5)

        # Carpeta de descarga
        path_frame = tk.Frame(self.root, bg=self.root['bg'])
        path_frame.pack()
        tk.Label(path_frame, text="Carpeta de descarga:", bg=self.root['bg']).pack(side=tk.LEFT)
        self.path_entry = tk.Entry(path_frame, width=50)
        self.path_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(path_frame, text="📁 Buscar", command=self.select_folder).pack(side=tk.LEFT)

        # Calidad
        quality_frame = tk.Frame(self.root, bg=self.root['bg'])
        quality_frame.pack(pady=5)
        tk.Label(quality_frame, text="Calidad:", bg=self.root['bg']).pack(side=tk.LEFT)
        self.quality_var = tk.StringVar()
        self.quality_menu = ttk.Combobox(quality_frame, textvariable=self.quality_var, state="readonly")
        self.quality_menu['values'] = ("Alta (mejor)", "Media (720p)", "Baja (360p)")
        self.quality_menu.current(0)
        self.quality_menu.pack(side=tk.LEFT)

        # Botones
        button_frame = tk.Frame(self.root, bg=self.root['bg'])
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="🔍 Cargar Playlist", command=self.load_playlist).pack(side=tk.LEFT, padx=10)
        self.download_button = tk.Button(button_frame, text="⬇️ Descargar Seleccionados", command=self.start_download_thread, state=tk.DISABLED)
        self.download_button.pack(side=tk.LEFT)

        # Área de videos
        self.canvas = tk.Canvas(self.root, height=250)
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Log
        self.log_area = scrolledtext.ScrolledText(self.root, height=8, state='disabled')
        self.log_area.pack(fill="x", padx=10, pady=10)

    def toggle_theme(self):
        if self.theme == "light":
            self.theme = "dark"
            self.root.configure(bg=self.bg_dark)
            self.theme_button.config(text="☀️ Modo Claro")
        else:
            self.theme = "light"
            self.root.configure(bg=self.bg_light)
            self.theme_button.config(text="🌙 Modo Oscuro")

        for widget in self.root.winfo_children():
            try:
                widget.configure(bg=self.root['bg'], fg=self.fg_dark if self.theme == "dark" else self.fg_light)
            except:
                pass

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, folder)

    def log(self, message):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    def load_playlist(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Advertencia", "Introduce la URL de la playlist.")
            return

        self.clear_videos()
        try:
            playlist = Playlist(url)
            self.log(f"🎵 Playlist encontrada: {playlist.title}")
            for video_url in playlist.video_urls:
                try:
                    yt = YouTube(video_url)
                    self.add_video_option(yt)
                except VideoUnavailable:
                    self.log(f"❌ Video no disponible: {video_url}")
        except RegexMatchError:
            messagebox.showerror("Error", "La URL de la playlist no es válida.")
        self.download_button.config(state=tk.NORMAL)

    def clear_videos(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.video_vars.clear()
        self.video_thumbnails.clear()

    def add_video_option(self, yt):
        var = tk.BooleanVar()
        self.video_vars.append((var, yt))

        frame = tk.Frame(self.scrollable_frame, padx=5, pady=5)
        frame.pack(fill='x', anchor='w')

        # Descargar miniatura
        try:
            response = requests.get(yt.thumbnail_url)
            img = Image.open(BytesIO(response.content)).resize((120, 70))
            thumbnail = ImageTk.PhotoImage(img)
            self.video_thumbnails.append(thumbnail)  # prevenir garbage collection
            tk.Label(frame, image=thumbnail).pack(side=tk.LEFT)
        except:
            pass

        tk.Checkbutton(frame, variable=var, text=yt.title, wraplength=600, anchor="w", justify="left").pack(side=tk.LEFT, fill="x")

    def start_download_thread(self):
        threading.Thread(target=self.download_selected_videos, daemon=True).start()

    def download_selected_videos(self):
        selected = [yt for var, yt in self.video_vars if var.get()]
        if not selected:
            messagebox.showinfo("Aviso", "Selecciona al menos un video para descargar.")
            return

        output_path = self.path_entry.get().strip() or './'
        os.makedirs(output_path, exist_ok=True)

        self.log(f"⬇️ Descargando {len(selected)} videos...\n")

        for yt in selected:
            try:
                self.log(f"🔸 Descargando: {yt.title}")
                stream = self.select_stream(yt)
                if stream:
                    stream.download(output_path=output_path)
                    self.log(f"✅ Completado: {yt.title}")
                else:
                    self.log(f"⚠️ No hay stream válido para: {yt.title}")
                time.sleep(1)
            except Exception as e:
                self.log(f"❌ Error en {yt.title}: {e}")

        self.log("\n🎉 ¡Descarga completada!")

    def select_stream(self, yt):
        quality = self.quality_var.get()
        if quality.startswith("Alta"):
            return yt.streams.get_highest_resolution()
        elif quality.startswith("Media"):
            return yt.streams.filter(res="720p", progressive=True).first()
        elif quality.startswith("Baja"):
            return yt.streams.filter(res="360p", progressive=True).first()
        return yt.streams.get_highest_resolution()


# Ejecutar la app
if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloaderApp(root)
    root.mainloop()
