# วิธีรัน : 
    Backend :
        # 1
        python -m venv venv 
        or
        py -m venv venv 

        # 2
        venv\Scripts\activate

        # 3
        pip install -r requirement.txt

        # 4
        docker compose up -d
        (if not working use docker compose down -v)

        # 5
        python app.py
        or 
        py app.py
    Frontend :
        # 1
        (window):                python -m http.server 8000
        (ถ้า linux/mac รันไม่ได้):   python3 -m http.server 8000

        # 2
        เข้าไปใน http://localhost:8000/

# jwt ,test and deploy soon ...
