# Link: https://www.bing.com/images/search?view=detailV2&ccid=9gj0uHGE&id=DE2964671C55A804983DC4F51C049807824487A5&thid=OIP.9gj0uHGEFgUd3cF_u1ujAwHaHZ&mediaurl=https%3a%2f%2fcompanieslogo.com%2fimg%2forig%2fJCI-48affaa2.png%3ft%3d1655544229&exph=1538&expw=1541&q=jci+logo+png&mode=overlay&FORM=IQFRBA&ck=D62BEE806AB2884B6AD37B9831668E6F&selectedIndex=0&idpp=serp
# pip install customtkinter

# Import
import os
import threading
import customtkinter as ctk
from PIL import Image
import time

# Configuration
TEST_SCRIPTS_FOLDER = "./Scripts"
COMPANY_NAME = "COMPANY NAME Inc."
TOOL_NAME = "Test Automation Engine"
COPYRIGHT = "© 2026-27 | | All rights reserved."

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{TOOL_NAME} - GUI")
        self.geometry("350x350")
        self.resizable(False, False)

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- 1. HEADER ---
        self.header = ctk.CTkFrame(self, fg_color="#90EE90", corner_radius=0)
        self.header.grid(row=0, column=0, sticky="ew")

        try:
            logo_image = ctk.CTkImage(light_image=Image.open("JCI.png"),
                                      dark_image=Image.open("JCI.png"),
                                      size=(40, 40))
            self.logo_label = ctk.CTkLabel(self.header, image=logo_image, text="")
        except:
            self.logo_label = ctk.CTkLabel(self.header, text="[LOGO]", font=("Arial", 16, "bold"))
        self.logo_label.pack(side="left", padx=20, pady=15)

        self.company_label = ctk.CTkLabel(self.header, text=f"{COMPANY_NAME}\n{TOOL_NAME}",
                                          font=("Arial", 12, "bold"), text_color="black")
        self.company_label.pack(side="right", padx=20, pady=10)

        # --- 2. MAIN CONTENT ---
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=1, column=0, pady=20)

        if not os.path.exists(TEST_SCRIPTS_FOLDER): os.makedirs(TEST_SCRIPTS_FOLDER)
        files = os.listdir(TEST_SCRIPTS_FOLDER)
        self.dropdown = ctk.CTkOptionMenu(self.main_frame, values=files if files else ["No scripts found"])
        self.dropdown.grid(row=0, column=0, pady=20, padx=20)
        self.dropdown.set("  Select Script ")

        self.btn_validate = ctk.CTkButton(self.main_frame, text="Validate Script", command=self.run_async_validate)
        self.btn_validate.grid(row=1, column=0, pady=5)

        self.btn_generate = ctk.CTkButton(self.main_frame, text="Generate Report", command=self.run_async_generate)
        self.btn_generate.grid(row=2, column=0, pady=5)

        # --- 3. BOTTOM SECTION ---
        # Status Label
        self.status_label = ctk.CTkLabel(self, text="Ready", text_color="gray")
        self.status_label.grid(row=2, column=0, pady=(5, 0))

        # Footer
        self.footer = ctk.CTkLabel(self, text=COPYRIGHT, font=("Arial", 10), text_color="gray")
        self.footer.grid(row=3, column=0, pady=(0, 5))

        # Progress Bar (Now at the very bottom)
        self.progress_bar = ctk.CTkProgressBar(self, width=300)
        self.progress_bar.grid(row=4, column=0, pady=(0, 10))
        self.progress_bar.set(0)

    # --- TASKS ---
    def update_progress(self, duration):
        self.progress_bar.set(0)
        steps = 50
        for i in range(steps + 1):
            time.sleep(duration / steps)
            self.progress_bar.set(i / steps)

    def run_async_validate(self):
        threading.Thread(target=self.validate_task, daemon=True).start()

    def run_async_generate(self):
        threading.Thread(target=self.generate_task, daemon=True).start()

    def validate_task(self):
        self.status_label.configure(text="Validating...", text_color="yellow")
        self.update_progress(3)
        self.status_label.configure(text="Validation Complete!", text_color="green")

    def generate_task(self):
        self.status_label.configure(text="Generating Report...", text_color="yellow")
        self.update_progress(5)
        self.status_label.configure(text="Report Ready!", text_color="green")

if __name__ == "__main__":
    app = App()
    app.mainloop()
