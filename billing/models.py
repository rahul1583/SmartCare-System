from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator

class Bill(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    )
    
    appointment = models.OneToOneField('appointments.Appointment', on_delete=models.CASCADE, related_name='bill', null=True, blank=True)
    prescription = models.OneToOneField('prescriptions.Prescription', on_delete=models.CASCADE, related_name='bill', null=True, blank=True)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bills')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_bills')
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    medicine_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    lab_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    additional_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bills'
        verbose_name = 'Bill'
        verbose_name_plural = 'Bills'
        ordering = ['-created_at']
    
    def __str__(self):
        if self.prescription:
            return f"Bill #{self.id} - {self.patient.get_full_name()} - Rs.{self.total_amount} (Prescription #{self.prescription.id})"
        else:
            return f"Bill #{self.id} - {self.patient.get_full_name()} - Rs.{self.total_amount}"
    
    def calculate_total(self):
        # Exclude medicine_fee from total_amount as per user request
        subtotal = (self.consultation_fee + self.lab_fee + 
                   self.other_fee + self.additional_charges - self.discount_amount)
        self.total_amount = subtotal + self.tax_amount
        self.save()
    
    def get_paid_amount(self):
        """Calculate total amount paid for this bill"""
        return sum(payment.amount for payment in self.payments.filter(status='completed'))
    
    def get_remaining_balance(self):
        """Calculate remaining balance for this bill"""
        return self.total_amount - self.get_paid_amount()

class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = (
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('esewa', 'eSewa'),
        ('khalti', 'Khalti'),
        ('bank_transfer', 'Bank Transfer'),
        ('online', 'Online Payment'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    transaction_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    paid_date = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payments'
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment #{self.id} - Rs.{self.amount} via {self.get_payment_method_display()}"

class BillItem(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'bill_items'
        verbose_name = 'Bill Item'
        verbose_name_plural = 'Bill Items'
    
    def __str__(self):
        return f"{self.description} - Rs.{self.total_price}"
    
    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)

class Refund(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=Payment.STATUS_CHOICES, default='pending')
    processed_date = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'refunds'
        verbose_name = 'Refund'
        verbose_name_plural = 'Refunds'
    
    def __str__(self):
        return f"Refund #{self.id} - Rs.{self.amount}"
