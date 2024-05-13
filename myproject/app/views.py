import os
import tempfile
from django.shortcuts import render, redirect, get_object_or_404
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
from io import BytesIO
import re
from datetime import datetime
from underthesea import classify
from .home import index
from .models import Document
from django.http import Http404
from mongoengine import Q
from django.http import HttpResponse





def convert_pdf_to_images(pdf_file):
    temp_dir = "../temp"
    os.makedirs(temp_dir, exist_ok=True) 

    images = convert_from_path(pdf_file, output_folder=temp_dir)
    image_paths = []

    # Lấy đường dẫn của các hình ảnh đã tạo
    for i, img in enumerate(images):
        img_path = os.path.join(temp_dir, f"page_{i+1}.jpg")
        img.save(img_path, "JPEG")
        image_paths.append(img_path)

    return image_paths



def process_file(request):
    if request.method == 'POST':
        if 'pdf' in request.FILES:
            pdf_file = request.FILES['pdf']
            mail = category = organization = date = combined_text = None  

            if 'identify' in request.POST:
                pdf_data = pdf_file.read()

                # Chuyển dữ liệu thành một đối tượng BytesIO
                pdf_data_io = BytesIO(pdf_data)

                # Tạo một tệp tạm thời để lưu trữ dữ liệu từ BytesIO
                with tempfile.NamedTemporaryFile(delete=False) as temp_pdf_file:
                    temp_pdf_file.write(pdf_data)
                    temp_pdf_path = temp_pdf_file.name

                # Chuyển đổi tệp PDF thành hình ảnh
                image_paths = convert_pdf_to_images(temp_pdf_path)

                recognized_text = []

                for img_path in image_paths:
                    img = Image.open(img_path)
                    text = pytesseract.image_to_string(img, lang='vie')
                    recognized_text.append(text)

                # Kết hợp văn bản từ các hình ảnh thành một chuỗi
                combined_text = '\n'.join(recognized_text)

                location, date = extract_date_from_text(combined_text)

                organization = extract_organization_name(combined_text)

                category = classify_text(combined_text)

                mail = extract_email(combined_text)

                number = extract_so_cong_van(combined_text)
                
                # Xóa tệp PDF tạm thời sau khi đã hoàn thành xử lý
                os.remove(temp_pdf_path)

                # Xóa các hình ảnh tạm thời sau khi đã sử dụng chúng
                for img_path in os.listdir('../temp'):
                    try:
                        os.remove('../temp/' + img_path)
                    except Exception as e:
                        print(f"Error deleting image {img_path}: {str(e)}")
                
            
            if 'save' in request.POST: 
                # Lưu vào cơ sở dữ liệu
                number = request.POST.get('number')
                organization_name = request.POST.get('organization')
                email = request.POST.get('email')
                issuance_date = request.POST.get('issued_date')
                field = request.POST.get('field') 

                data = Document(
                    number=number,
                    pdf_file=pdf_file,
                    organization_name=organization_name,
                    email=email,
                    issuance_date=issuance_date,
                    field=field
                )
                data.save()
              

            return render(request, 'app/upload.html', {'email': mail, 'type': category, 'organization': organization, 'date': date, 'text': combined_text, 'so': number})
        
    return render(request, 'app/upload.html')


# Homepage ############################
def home(request):
    return index(request)

# Table ###############################
def tables(request):
    documents = Document.objects.all()
    return render(request, 'app/tables.html', {'documents': documents})

# Delete ###############################
def delete_document(request, document_id):
    try:
        document = Document.objects.get(pk=document_id)
    except Document.DoesNotExist:
        raise Http404("Document does not exist")
    
    if request.method == 'POST':
        document.delete()
        return redirect(request.META.get('HTTP_REFERER', 'home'))
    
    return render(request, 'app/tables.html', {'document': document})

# Edit ###################################
def edit_document(request, document_id):
    document = Document.objects.get(pk=document_id)
    # Truyền dữ liệu của document vào form
    context = {
        'document': document
    }
    return render(request, 'app/edit.html', context)

# Update #################################
def update_document(request, document_id):
    document = Document.objects.get(pk=document_id)
    if request.method == 'POST':
        # Lấy dữ liệu mới 
        number = request.POST.get('number')
        organization_name = request.POST.get('organization')
        email = request.POST.get('email')
        issuance_date = request.POST.get('issued_date')
        field = request.POST.get('field')
        
        # Cập nhật thông tin
        document.number = number
        document.organization_name = organization_name
        document.email = email
        document.issuance_date = issuance_date
        document.field = field
        document.save() 

        return redirect('tables')

    return render(request, 'app/tables.html', {'document': document})


from mongoengine import Q

def search_documents(request):
    query = request.GET.get('query')
    if query:
        # Tách truy vấn thành các từ riêng
        keywords = query.split()
        
        # Tạo danh sách các điều kiện tìm kiếm
        conditions = Q()
        for keyword in keywords:
            conditions |= (Q(organization_name__icontains=keyword) |
                            Q(email__icontains=keyword) |
                            Q(field__icontains=keyword) |
                            Q(number__icontains=keyword)|
                            Q(issuance_date__icontains=keyword))
        
        documents = Document.objects.filter(conditions)
    else:
        documents = Document.objects.all()
    
    return render(request, 'app/search.html', {'documents': documents, 'query': query})





# Download ###################################
def download_document(request, document_id):
    # Tìm đối tượng Document 
    document = Document.objects.get(pk=document_id)

    pdf_data = document.pdf_file.read()

    # Tạo response để trả về tệp dữ liệu
    response = HttpResponse(pdf_data, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{document.organization_name}.pdf"'
    return response


######################## hàm xử lý rút trích thông tin văn bản ###########################

def extract_date_from_text(text):
    # Mẫu nhận dạng ngày tháng năm: "(tên địa danh) ngày xx tháng xx năm xxxx"
    pattern = r"(\D+) ngày (\d{1,2}) tháng (\d{1,2}) năm (\d{4})"
    matches = re.findall(pattern, text)

    if matches:
        # Lấy thông tin tên địa danh, ngày, tháng, năm 
        location, day, month, year = matches[0]
        day = int(day)
        month = int(month)
        year = int(year)


        try:
            formatted_date = datetime(year, month, day).strftime('%d/%m/%Y')
            return location.strip(), formatted_date
        except ValueError:
            return None, None
    else:
        return None, None



def extract_organization_name(text):
    # tên cơ quan được đặt sau từ khóa "Cơ quan:"
    match = re.search(r'Cơ quan:\s*(.*)', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    else:
        return None

def extract_so_cong_van(text):
    # tìm số công văn
    pattern = r'Số:\s*(\d+\/[A-Z]+)'
    
    # Tìm kiếm mẫu trong văn bản
    match = re.search(pattern, text)
    

    if match:
        return match.group(1) 
    else:
        return None  

def classify_text(text):
    keywords = {
        'Khoa học': ['khoa học', 'nghiên cứu', 'kỹ thuật', 'công nghệ'],
        'Kinh tế': ['kinh tế', 'tài chính', 'doanh nghiệp', 'thị trường'],
        'Y tế': ['y tế', 'bệnh', 'bác sĩ', 'benh vien'],
        'Công nghệ': ['công nghệ', 'thiết bị', 'ứng dụng', 'máy tính'],
        'Chính trị': ['chính trị', 'chính phủ', 'bầu cử', 'quốc hội']
    }
    
    # Đếm số lần xuất hiện của từ khóa
    counts = {field: 0 for field in keywords}
    for field, field_keywords in keywords.items():
        for keyword in field_keywords:
            counts[field] += text.lower().count(keyword)

    max_count = max(counts.values())
    max_field = next((field for field, count in counts.items() if count == max_count), None)

    default_field = "khác"
    return max_field if max_count > 0 else default_field



def extract_email(text):
    match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if match:
        return match.group(0)
    else:
        return None


