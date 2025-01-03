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
        self.thumbnail_cache = {}  # Dictionary to store thumbnails
        self.current_full_size_image = None  # To store the last opened full size image
        self.zoom_level = 1.0  # zoom level
        self.zoom_bar_width = 200  # Initial width of zoom bar
        self.zoom_percentage_var = tk.StringVar(value="100%")
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.image_x_offset = 0
        self.image_y_offset = 0
        self.image_width = 0
        self.image_height = 0
        self.window_width = 0
        self.window_height = 0
        self.current_zoom_image = None  # stores the current zoom image
        self.canvas = None
        self.canvas_image = None
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
        self.thumbnail_cache = {}
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

    def get_thumbnail(self, filepath):
        if filepath in self.thumbnail_cache:
            return self.thumbnail_cache[filepath]
        else:
            img = Image.open(filepath)
            img.thumbnail((200, 200))
            photo_image = ImageTk.PhotoImage(img)
            self.thumbnail_cache[filepath] = photo_image
            return photo_image

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
                photo_image = self.get_thumbnail(filepath)

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

    def open_full_size_image(self, event, filepath):
        try:
            img = Image.open(filepath)
            self.current_full_size_image = img  # stores the current image to use when rotating and zooming.
            if self.full_size_window:
                self.full_size_window.destroy()
            self.full_size_window = tk.Toplevel(self.root)
            self.full_size_window.title(os.path.basename(filepath))
            # Zoom Control Frame
            zoom_control_frame = ttk.Frame(self.full_size_window)
            zoom_control_frame.pack(fill=tk.X, padx=5, pady=5)

            # Zoom out Button
            ttk.Button(zoom_control_frame, text="-", width=3, command=lambda: self.zoom_image(0.9)).pack(side=tk.LEFT,
                                                                                                         padx=5)

            # Zoom Scale
            self.zoom_percentage_var = tk.StringVar(value="100%")
            zoom_percentage_label = ttk.Label(zoom_control_frame, textvariable=self.zoom_percentage_var, width=5)
            zoom_percentage_label.pack(side=tk.LEFT, padx=5)

            # Zoom In Button
            ttk.Button(zoom_control_frame, text="+", width=3, command=lambda: self.zoom_image(1.1)).pack(side=tk.LEFT,
                                                                                                         padx=5)
            # Canvas Creation
            self.canvas = tk.Canvas(self.full_size_window)
            self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            self.full_size_image = ImageTk.PhotoImage(img)
            self.canvas_image = self.canvas.create_image(0, 0, image=self.full_size_image, anchor=tk.NW)
            # Calculate window size with 100px padding
            self.window_width = self.full_size_image.width() + 100
            self.window_height = self.full_size_image.height() + 100
            self.full_size_window.geometry(f"{self.window_width}x{self.window_height}")

            # Calculate Image Boundaries
            self.image_width = self.full_size_image.width()
            self.image_height = self.full_size_image.height()
            # Image Info
            info_frame = ttk.Frame(self.full_size_window)
            info_frame.pack(pady=5)

            ttk.Label(info_frame, text=f"Filename: {os.path.basename(filepath)}").pack()
            ttk.Label(info_frame, text=f"Dimensions: {img.width}x{img.height}").pack()
            date_taken = self.extract_date(filepath)
            if date_taken:
                ttk.Label(info_frame, text=f"Date Taken: {date_taken.strftime('%Y-%m-%d')}").pack()
            else:
                file_date = self.get_file_modification_date(filepath)
                ttk.Label(info_frame, text=f"Date Modified: {file_date.strftime('%Y-%m-%d')}").pack()

            # Bind image for rotate, panning
            self.canvas.tag_bind(self.canvas_image, "<Button-1>",
                                 lambda event: self.handle_image_click(event, filepath))
            self.canvas.tag_bind(self.canvas_image, "<ButtonPress-1>", self.start_pan)
            self.canvas.tag_bind(self.canvas_image, "<B1-Motion>", self.pan_image)
        except Exception as e:
            messagebox.showerror("Error", f"Error opening image: {e}")

    def handle_image_click(self, event, filepath):
        if event.state & 0x0004:  # Shift key is pressed
            self.rotate_image(90)

    def start_pan(self, event):
        self.pan_start_x = event.x
        self.pan_start_y = event.y

    def pan_image(self, event):
        if self.current_full_size_image:
            dx = event.x - self.pan_start_x
            dy = event.y - self.pan_start_y

            # Calculate the new offsets
            new_x_offset = self.image_x_offset + dx
            new_y_offset = self.image_y_offset + dy

            # Calculate the bounds of the image
            img_width = int(self.current_full_size_image.width * self.zoom_level)
            img_height = int(self.current_full_size_image.height * self.zoom_level)

            max_x = 0
            min_x = self.window_width - img_width
            max_y = 0
            min_y = self.window_height - img_height

            # Apply bounds
            if img_width > self.window_width:
                new_x_offset = max(min(new_x_offset, max_x), min_x)
            else:
                new_x_offset = (self.window_width - img_width) / 2
            if img_height > self.window_height:
                new_y_offset = max(min(new_y_offset, max_y), min_y)
            else:
                new_y_offset = (self.window_height - img_height) / 2

            self.image_x_offset = new_x_offset
            self.image_y_offset = new_y_offset

            self.pan_start_x = event.x
            self.pan_start_y = event.y

            self.canvas.move(self.canvas_image, dx, dy)

    def rotate_image(self, angle):
        if self.current_full_size_image:
            rotated_img = self.current_full_size_image.rotate(angle, expand=True)
            self.current_full_size_image = rotated_img
            self.current_zoom_image = ImageTk.PhotoImage(rotated_img)
            self.canvas.itemconfig(self.canvas_image, image=self.current_zoom_image)
            self.image_x_offset = 0
            self.image_y_offset = 0
            self.canvas.move(self.canvas_image, -self.canvas.coords(self.canvas_image)[0] + self.image_x_offset,
                             -self.canvas.coords(self.canvas_image)[1] + self.image_y_offset)
            self.image_width = self.current_zoom_image.width()
            self.image_height = self.current_zoom_image.height()
            window_width = self.image_width + 100
            window_height = self.image_height + 100
            self.full_size_window.geometry(f"{window_width}x{window_height}")

    def zoom_image(self, zoom_factor):
        if self.current_full_size_image:
            self.zoom_level *= zoom_factor
            width = int(self.current_full_size_image.width * self.zoom_level)
            height = int(self.current_full_size_image.height * self.zoom_level)
            zoomed_img = self.current_full_size_image.resize((width, height))
            self.current_zoom_image = ImageTk.PhotoImage(zoomed_img)
            self.canvas.itemconfig(self.canvas_image, image=self.current_zoom_image)
            self.image_x_offset = 0
            self.image_y_offset = 0
            self.canvas.move(self.canvas_image, -self.canvas.coords(self.canvas_image)[0] + self.image_x_offset,
                             -self.canvas.coords(self.canvas_image)[1] + self.image_y_offset)
            self.image_width = self.current_zoom_image.width()
            self.image_height = self.current_zoom_image.height()
            window_width = self.image_width + 100
            window_height = self.image_height + 100
            self.full_size_window.geometry(f"{window_width}x{window_height}")
            zoom_percentage = int(self.zoom_level * 100)
            self.zoom_percentage_var.set(f"{zoom_percentage}%")

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