import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ExifTags
import os
from datetime import datetime
import threading
import subprocess


class PhotoViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Photo Archive Viewer")

        self.archive_path = None
        self.photo_data = []  # List of (filepath, datetime)
        self.current_page = 1
        self.photos_per_page = 12  # Initial number of photos per page
        self.grid_cols = 4  # Initial grid columns
        self.loading_label = None  # To show loading message
        self.filtered_date = None  # date filtering
        self.image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp')
        self.sort_by_date = True
        self.full_size_window = None

        # UI elements
        self.create_widgets()

    def create_widgets(self):
        # Menu
        menu_bar = tk.Menu(self.root)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Open Archive", command=self.open_archive)
        file_menu.add_command(label="Open Folder", command=self.open_folder)
        menu_bar.add_cascade(label="File", menu=file_menu)
        self.root.config(menu=menu_bar)

        # Control Frame (Date sort, grid size and pagination)
        control_frame = ttk.Frame(self.root, padding=10)
        control_frame.pack(fill=tk.X)

        # Date Filtering
        ttk.Label(control_frame, text="Filter Date (YYYY-MM-DD):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.date_filter_var = tk.StringVar()
        self.date_filter_entry = ttk.Entry(control_frame, textvariable=self.date_filter_var, width=12)
        self.date_filter_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Button(control_frame, text="Filter by Date", command=self.filter_by_date).grid(row=0, column=2, padx=5,
                                                                                           pady=5, sticky=tk.W)
        ttk.Button(control_frame, text="Reset Filter", command=self.reset_filter).grid(row=0, column=3, padx=5, pady=5,
                                                                                       sticky=tk.W)

        # Grid Size Control
        ttk.Label(control_frame, text="Grid Columns:").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.grid_cols_var = tk.IntVar(value=self.grid_cols)
        grid_cols_spinbox = ttk.Spinbox(control_frame, from_=1, to=10, textvariable=self.grid_cols_var, width=3)
        grid_cols_spinbox.grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)
        ttk.Button(control_frame, text="Set Grid", command=self.update_grid).grid(row=0, column=6, padx=5, pady=5,
                                                                                  sticky=tk.W)

        # Pagination Control
        ttk.Label(control_frame, text="Photos per page:").grid(row=0, column=7, padx=5, pady=5, sticky=tk.W)
        self.photos_per_page_var = tk.IntVar(value=self.photos_per_page)
        photos_per_page_spinbox = ttk.Spinbox(control_frame, from_=1, to=24, textvariable=self.photos_per_page_var,
                                              width=3)
        photos_per_page_spinbox.grid(row=0, column=8, padx=5, pady=5, sticky=tk.W)
        ttk.Button(control_frame, text="Set Photos per Page", command=self.update_photos_per_page).grid(row=0, column=9,
                                                                                                        padx=5, pady=5,
                                                                                                        sticky=tk.W)

        self.page_label = ttk.Label(control_frame, text=f"Page: {self.current_page}")
        self.page_label.grid(row=0, column=10, padx=5, pady=5, sticky=tk.W)
        ttk.Button(control_frame, text="Previous", command=self.prev_page).grid(row=0, column=11, padx=5, pady=5,
                                                                                sticky=tk.W)
        ttk.Button(control_frame, text="Next", command=self.next_page).grid(row=0, column=12, padx=5, pady=5,
                                                                            sticky=tk.W)

        # Photo Display Frame
        self.photo_frame = ttk.Frame(self.root, padding=10)
        self.photo_frame.pack(fill=tk.BOTH, expand=True)

    def open_archive(self):
        self.archive_path = filedialog.askdirectory(title="Select Photo Archive Folder")
        self.sort_by_date = True
        if self.archive_path:
            self.start_loading_photos()

    def open_folder(self):
        self.archive_path = filedialog.askdirectory(title="Select Photo Folder")
        self.sort_by_date = False
        if self.archive_path:
            self.start_loading_photos()

    def start_loading_photos(self):
        self.show_loading_indicator("Loading photos...")
        threading.Thread(target=self.load_photos, daemon=True).start()

    def show_loading_indicator(self, text):
        if self.loading_label:
            self.loading_label.destroy()
        self.loading_label = ttk.Label(self.photo_frame, text=text)
        self.loading_label.pack(pady=20)
        self.root.update_idletasks()

    def hide_loading_indicator(self):
        if self.loading_label:
            self.loading_label.destroy()
            self.loading_label = None

    def extract_date(self, image_path):
        try:
            img = Image.open(image_path)
            exif_data = img._getexif()
            if exif_data:
                for tag_id, tag_value in exif_data.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    if tag == 'DateTimeOriginal':
                        date_str = tag_value.split(' ')[0]
                        return datetime.strptime(date_str, '%Y:%m:%d')
            return None
        except Exception as e:
            print(f"Error extracting date from {image_path}: {e}")
            return None

    def get_file_modification_date(self, filepath):
        timestamp = os.path.getmtime(filepath)
        return datetime.fromtimestamp(timestamp)

    def load_photos(self):
        self.photo_data = []
        if self.archive_path:
            for filename in os.listdir(self.archive_path):
                if filename.lower().endswith(self.image_extensions):
                    filepath = os.path.join(self.archive_path, filename)

                    date_taken = self.extract_date(filepath)
                    if self.sort_by_date:  # if archive
                        if date_taken:
                            self.photo_data.append((filepath, date_taken))
                    else:  # if folder
                        if date_taken:
                            self.photo_data.append((filepath, date_taken))
                        else:
                            file_date = self.get_file_modification_date(filepath)
                            self.photo_data.append((filepath, file_date))

        if self.sort_by_date:
            self.photo_data.sort(key=lambda item: item[1])
        self.current_page = 1
        self.filtered_date = None
        self.root.after(0, self.display_photos)
        self.root.after(0, self.hide_loading_indicator)

    def filter_by_date(self):
        filter_date_str = self.date_filter_var.get()
        try:
            if filter_date_str:
                self.filtered_date = datetime.strptime(filter_date_str, '%Y-%m-%d').date()
            else:
                self.filtered_date = None
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Please use YYYY-MM-DD.")
            return
        self.current_page = 1
        self.display_photos()

    def reset_filter(self):
        self.date_filter_var.set("")
        self.filtered_date = None
        self.current_page = 1
        self.display_photos()

    def update_grid(self):
        self.grid_cols = self.grid_cols_var.get()
        self.display_photos()

    def update_photos_per_page(self):
        self.photos_per_page = self.photos_per_page_var.get()
        self.current_page = 1
        self.display_photos()

    def display_photos(self):

        for widget in self.photo_frame.winfo_children():
            widget.destroy()

        if not self.photo_data:
            ttk.Label(self.photo_frame, text="No photos found in the archive.").pack(padx=20, pady=20)
            return

        start_index = (self.current_page - 1) * self.photos_per_page
        end_index = start_index + self.photos_per_page

        photos_to_display = self.get_filtered_photos()[start_index:end_index]

        row_num = 0
        col_num = 0

        for item in photos_to_display:
            filepath = item[0]
            try:
                img = Image.open(filepath)
                img.thumbnail((200, 200))
                photo_image = ImageTk.PhotoImage(img)

                label_frame = ttk.Frame(self.photo_frame)  # Frame for each image + label
                label_frame.grid(row=row_num, column=col_num, padx=5, pady=5)

                label = ttk.Label(label_frame, image=photo_image)
                label.image = photo_image
                label.pack()

                filename = os.path.basename(filepath)
                name_label = ttk.Label(label_frame, text=filename)
                name_label.pack()

                # Bind right-click to show context menu
                label.bind("<Button-3>", lambda event, path=filepath: self.show_context_menu(event, path))
                # Bind left-click to show full size image
                label.bind("<Button-1>", lambda event, path=filepath: self.open_full_size_image(event, path))

                col_num += 1
                if col_num >= self.grid_cols:
                    col_num = 0
                    row_num += 1

            except Exception as e:
                print(f"Error displaying image {filepath}: {e}")

        self.update_page_label()

    def show_context_menu(self, event, filepath):
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="Show in Folder", command=lambda: self.execute_show_in_folder(filepath))
        context_menu.tk_popup(event.x_root, event.y_root)

    def execute_show_in_folder(self, filepath):
        self.show_in_folder(filepath)

    def show_in_folder(self, filepath):
        if not os.path.exists(filepath):
            messagebox.showerror("Error", "File not found")
            return

        try:
            if os.name == 'nt':  # Windows
                subprocess.Popen(['explorer', '/select,', filepath.replace("/", "\\")])
            elif os.name == 'posix':  # macOS or Linux
                if os.uname().sysname == "Darwin":  # macOS
                    subprocess.Popen(['open', '-R', filepath])
                elif os.uname().sysname == "Linux":
                    try:  # try with nautilus
                        subprocess.Popen(
                            ['nautilus', os.path.dirname(filepath), '--select', os.path.basename(filepath)])
                    except FileNotFoundError:
                        try:  # Try with dolphin
                            subprocess.Popen(['dolphin', '--select', filepath])
                        except FileNotFoundError:  # try with xdg-open
                            subprocess.Popen(['xdg-open', os.path.dirname(filepath)])

        except Exception as e:
            messagebox.showerror("Error", f"Error opening folder: {e}")

    def open_full_size_image(self,event,filepath):
        try:
            img = Image.open(filepath)
            if self.full_size_window:
                self.full_size_window.destroy()
            self.full_size_window = tk.Toplevel(self.root)
            self.full_size_window.title(os.path.basename(filepath))
            photo_image = ImageTk.PhotoImage(img)
            label = ttk.Label(self.full_size_window, image=photo_image)
            label.image=photo_image
            label.pack(padx=10, pady=10)
             # Calculate window size with 100px padding
            window_width = photo_image.width() + 100
            window_height = photo_image.height() + 100
            self.full_size_window.geometry(f"{window_width}x{window_height}")
        except Exception as e:
             messagebox.showerror("Error", f"Error opening image: {e}")

    def get_filtered_photos(self):
        if self.filtered_date:
            return [item for item in self.photo_data if item[1] and item[1].date() == self.filtered_date]
        else:
            return self.photo_data

    def update_page_label(self):
        total_photos = len(self.get_filtered_photos())
        total_pages = (total_photos + self.photos_per_page - 1) // self.photos_per_page
        self.page_label.config(text=f"Page: {self.current_page} / {max(1, total_pages)}")

    def next_page(self):
        total_photos = len(self.get_filtered_photos())
        total_pages = (total_photos + self.photos_per_page - 1) // self.photos_per_page
        if self.current_page < total_pages:
            self.current_page += 1
            self.display_photos()

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.display_photos()


if __name__ == "__main__":
    root = tk.Tk()
    app = PhotoViewerApp(root)
    root.mainloop()