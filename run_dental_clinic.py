import os
import sys
from app import app

if __name__ == '__main__':
    # تعيين المسار الحالي كمسار عمل
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # تشغيل التطبيق
    app.run(debug=False, host='127.0.0.1', port=5000)
