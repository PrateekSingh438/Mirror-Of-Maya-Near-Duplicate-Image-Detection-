## Clone and Run the Repository

1) Clone the repository
git clone https://github.com/PrateekSingh438/Mirror-Of-Maya-Near-Duplicate-Image-Detection.git

2) Navigate into the project
cd Mirror-Of-Maya-Near-Duplicate-Image-Detection

3) Create a virtual environment
python -m venv venv

4) Activate the virtual environment

Windows:
venv\Scripts\activate

Linux / macOS:
source venv/bin/activate

5) Install dependencies
pip install -r requirements.txt

6) Add your image dataset
Place all images inside the "dataset" folder in the project root.

7) Run the system
streamlit run app.py

The system will index images, detect near duplicates, and print matching image pairs.
If ground truth is provided, evaluation metrics will also be shown.
