from django import forms
from .models import Payment, Bill

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['payment_method', 'amount', 'notes']
        widgets = {
            'payment_method': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Any additional notes for this payment...'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.bill = kwargs.pop('bill', None)
        super().__init__(*args, **kwargs)
        
        if self.bill:
            # Set max amount to remaining balance
            remaining_balance = self.bill.total_amount - self.bill.get_paid_amount()
            self.fields['amount'].widget.attrs['max'] = remaining_balance
            self.fields['amount'].widget.attrs['placeholder'] = f'Maximum: Rs. {remaining_balance}'
            
            # Pre-fill with remaining balance
            if not self.initial.get('amount'):
                self.fields['amount'].initial = remaining_balance
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if self.bill and amount > 0:
            remaining_balance = self.bill.total_amount - self.bill.get_paid_amount()
            if amount > remaining_balance:
                raise forms.ValidationError(f'Payment amount cannot exceed remaining balance of Rs. {remaining_balance}')
        return amount

class BillForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = ['consultation_fee', 'additional_charges', 'discount_amount', 'tax_amount', 'due_date', 'notes']
        widgets = {
            'consultation_fee': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0'
            }),
            'additional_charges': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0'
            }),
            'discount_amount': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0'
            }),
            'tax_amount': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0'
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'type': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Any notes about this bill...'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.appointment = kwargs.pop('appointment', None)
        super().__init__(*args, **kwargs)
        
        if self.appointment and self.appointment.doctor.doctor_profile:
            # Pre-fill consultation fee with doctor's fee
            if not self.initial.get('consultation_fee'):
                self.fields['consultation_fee'].initial = self.appointment.doctor.doctor_profile.consultation_fee
