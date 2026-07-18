
# pip install customtkinter
#IMPORT
import os
import threading
import tkinter as tk
import customtkinter as ctk

# Configuration
TEST_SCRIPTS_FOLDER = "./Scripts"
COMPANY_NAME = "Tech Solutions Inc."
TOOL_NAME = "Test Automation Engine"
COPYRIGHT = "© 2026 Tech Solutions Inc. All rights reserved."

# SYSTEM
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# APP CLASS
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"{TOOL_NAME} - GUI")
        self.geometry("350x400")

        # --- ICON SETUP ---
        # Ensure you have an 'icon.png' in your directory
        try:
            self.iconphoto(False, tk.PhotoImage(file="icon.png"))
        except:
            print("Icon file not found, skipping...")

        # Grid configuration for layout
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- 1. HEADER ---
        self.header = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=0)
        self.header.grid(row=0, column=0, sticky="ew")

        # Logo Placeholder (Text-based)
        self.logo_label = ctk.CTkLabel(self.header, text="[LOGO]", font=("Arial", 16, "bold"), text_color="#1f6aa5")
        self.logo_label.pack(side="left", padx=20, pady=15)

        self.company_label = ctk.CTkLabel(self.header, text=f"{COMPANY_NAME}\n{TOOL_NAME}", font=("Arial", 12, "bold"))
        self.company_label.pack(side="right", padx=20, pady=10)

        # --- 2. MAIN CONTENT ---
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=1, column=0, pady=20)

        # Automatically fetch file names
        if not os.path.exists(TEST_SCRIPTS_FOLDER):
            os.makedirs(TEST_SCRIPTS_FOLDER)

        files = os.listdir(TEST_SCRIPTS_FOLDER)
        self.dropdown = ctk.CTkOptionMenu(self.main_frame, values=files if files else ["No scripts found"])
        self.dropdown.grid(row=0, column=0, pady=20, padx=20)
        self.dropdown.set("Select a Script")

        # Buttons
        self.btn_validate = ctk.CTkButton(self.main_frame, text="Validate Script", command=self.run_async_validate)
        self.btn_validate.grid(row=1, column=0, pady=5)

        self.btn_generate = ctk.CTkButton(self.main_frame, text="Generate Report", command=self.run_async_generate)
        self.btn_generate.grid(row=2, column=0, pady=5)

        self.btn_cancel = ctk.CTkButton(self.main_frame, text="Cancel", fg_color="#d9534f", hover_color="#c9302c",
                                        command=self.destroy)
        self.btn_cancel.grid(row=3, column=0, pady=5)

        # --- 3. FOOTER ---
        self.footer = ctk.CTkLabel(self, text=COPYRIGHT, font=("Arial", 10), text_color="gray")
        self.footer.grid(row=2, column=0, pady=10)

        # Status Label
        self.status_label = ctk.CTkLabel(self, text="Ready", text_color="gray")
        self.status_label.grid(row=2, column=0, pady=10)

    # --- THREADING LOGIC ---
    def run_async_validate(self):
        # Starts the task in a separate thread so GUI doesn't freeze
        thread = threading.Thread(target=self.validate_task)
        thread.start()

    def run_async_generate(self):
        thread = threading.Thread(target=self.generate_task)
        thread.start()

    # --- BACKGROUND TASKS ---
    def validate_task(self):
        self.status_label.configure(text="Validating...", text_color="yellow")
        # --- Simulate heavy work ---
        import time
        time.sleep(3)
        self.status_label.configure(text="Validation Complete!", text_color="green")

    def generate_task(self):
        self.status_label.configure(text="Generating Report...", text_color="yellow")
        # --- CALL YOUR REPORT GENERATOR HERE ---
        # finalize_html_report("test_results.csv")
        import time
        time.sleep(5)
        self.status_label.configure(text="Report Ready!", text_color="green")


if __name__ == "__main__":
    app = App()
    app.mainloop()
