import mongoengine

class Document(mongoengine.Document):
    organization_name = mongoengine.StringField(max_length=100, verbose_name='Tên cơ quan')
    email = mongoengine.EmailField(verbose_name='Email')
    issuance_date = mongoengine.DateField(verbose_name='Ngày ban hành')
    field = mongoengine.StringField(max_length=100, verbose_name='Lĩnh vực')
    pdf_file = mongoengine.FileField(upload_to='pdfs/', verbose_name='File PDF')
    number = mongoengine.StringField(verbose_name='so cong van')
    created_at = mongoengine.DateTimeField(auto_now_add=True, verbose_name='Thời gian tạo')


    def __str__(self):
        return self.organization_name
