from django import forms
from django.contrib.auth.forms import (
    UserCreationForm,
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
)
from django.core.exceptions import ValidationError
from .models import CustomUser, Answer, ExamAttempt
import re


class StudentRegistrationForm(UserCreationForm):
    """Form for student registration"""

    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter first name",
                "id": "firstName",
            }
        ),
    )

    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter last name",
                "id": "lastName",
            }
        ),
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "your.email@example.com",
                "id": "email",
            }
        ),
    )

    phone = forms.CharField(
        max_length=17,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "+263 712 345 678",
                "id": "phone",
            }
        ),
    )

    school = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your school name",
                "id": "school",
            }
        ),
    )

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Create a strong password",
                "id": "password",
            }
        ),
    )

    password2 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Re-enter your password",
                "id": "confirmPassword",
            }
        ),
    )

    terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={"id": "terms"}),
        error_messages={"required": "You must accept the terms and conditions"},
    )

    class Meta:
        model = CustomUser
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "school",
            "password1",
            "password2",
        ]

    def clean_email(self):
        """Validate email is unique"""
        email = self.cleaned_data.get("email")
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered.")
        return email

    def clean_phone(self):
        """Validate and format phone number"""
        phone = self.cleaned_data.get("phone")
        # Remove spaces and dashes
        phone = re.sub(r"[\s\-]", "", phone)

        # Check if phone starts with country code
        if not phone.startswith("+"):
            if phone.startswith("0"):
                phone = "+263" + phone[1:]  # Zimbabwe country code
            else:
                phone = "+263" + phone

        # Validate phone number format
        if not re.match(r"^\+?1?\d{9,15}$", phone):
            raise ValidationError("Enter a valid phone number.")

        # Check if phone is unique
        if CustomUser.objects.filter(phone=phone).exists():
            raise ValidationError("This phone number is already registered.")

        return phone

    def clean_password1(self):
        """Validate password strength"""
        password = self.cleaned_data.get("password1")

        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")

        # Check for at least one uppercase and one lowercase
        if not re.search(r"[a-z]", password) or not re.search(r"[A-Z]", password):
            raise ValidationError(
                "Password must contain both uppercase and lowercase letters."
            )

        # Check for at least one number
        if not re.search(r"\d", password):
            raise ValidationError("Password must contain at least one number.")

        return password

    def save(self, commit=True):
        """Save user with additional fields"""
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]  # Use email as username
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.phone = self.cleaned_data["phone"]
        user.school = self.cleaned_data["school"]

        if commit:
            user.save()
        return user


class StudentLoginForm(AuthenticationForm):
    """Form for student login"""

    username = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your email",
                "id": "email",
            }
        ),
    )

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your password",
                "id": "password",
            }
        )
    )

    remember_me = forms.BooleanField(required=False, widget=forms.CheckboxInput())


class ProfileUpdateForm(forms.ModelForm):
    """Form for updating student profile"""

    class Meta:
        model = CustomUser
        fields = ["first_name", "last_name", "email", "phone", "school", "student_id", "profile_picture"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "readonly": "readonly"}
            ),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "school": forms.TextInput(attrs={"class": "form-control"}),
            "student_id": forms.TextInput(attrs={"class": "form-control"}),
            "profile_picture": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
        }

    def clean_phone(self):
        """Validate phone number"""
        phone = self.cleaned_data.get("phone")
        if phone and (
            CustomUser.objects.filter(phone=phone)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise ValidationError("This phone number is already in use.")
        return phone

    def clean_profile_picture(self):
        """Validate uploaded profile picture size and type."""
        picture = self.cleaned_data.get("profile_picture")
        if picture and hasattr(picture, "size"):
            if picture.size > 5 * 1024 * 1024:  # 5 MB limit
                raise ValidationError("Profile picture must be smaller than 5 MB.")
        return picture


class ExamAnswerForm(forms.ModelForm):
    """Form for submitting exam answers"""

    class Meta:
        model = Answer
        fields = ["answer_text"]
        widgets = {
            "answer_text": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter your answer here...",
                }
            )
        }

    def __init__(self, *args, **kwargs):
        question = kwargs.pop("question", None)
        super().__init__(*args, **kwargs)

        if question:
            # Customize widget based on question type

            if question.question_type == "mcq":
                choices = []
                if question.option_a:
                    choices.append(("A", question.option_a))
                if question.option_b:
                    choices.append(("B", question.option_b))
                if question.option_c:
                    choices.append(("C", question.option_c))
                if question.option_d:
                    choices.append(("D", question.option_d))

                self.fields["answer_text"] = forms.ChoiceField(
                    choices=choices,
                    widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
                )

            elif question.question_type == "true_false":
                self.fields["answer_text"] = forms.ChoiceField(
                    choices=[("True", "True"), ("False", "False")],
                    widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
                )

            elif question.question_type == "short_answer":
                self.fields["answer_text"].widget = forms.TextInput(
                    attrs={
                        "class": "form-control",
                        "class": "form-control",
                        "placeholder": "Enter your answer.....",
                    }
                )

            elif question.question_type == "code":
                self.fields["answer_text"].widget = forms.TextInput(
                    attrs={
                        "class": "form-control",
                        "class": "form-control",
                        "placeholder": "Enter your code.....",
                    }
                )


class ContactForm(forms.Form):
    """Contact form for students"""

    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Enter your name"}
        ),
    )

    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "Enter your email"}
        )
    )

    phone = forms.CharField(
        max_length=17,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Enter your number"}
        ),
    )

    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "What is this regarding"}
        ),
    )

    message = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "row": 5,
                "placeholder": "Tell us how we can help you.....",
            }
        )
    )


# =========================================
# PASSWORD RESET FORMS
# =========================================


class CustomPasswordResetForm(PasswordResetForm):
    """Custom password reset form with styled email field"""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your registered email address",
                "id": "id_email",
            }
        ),
    )

    def clean_email(self):
        """Validate that the email exists in the system"""
        email = self.cleaned_data.get("email")
        if not CustomUser.objects.filter(email=email).exists():
            raise ValidationError("No account found with this email address.")
        return email


class CustomSetPasswordForm(SetPasswordForm):
    """Custom password reset form with styled password fields"""

    new_password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your new password",
                "id": "id_new_password1",
            }
        ),
        help_text="Password must be at least 8 characters long.",
    )

    new_password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Re-enter your new password",
                "id": "id_new_password2",
            }
        ),
        help_text="Enter the same password for verification.",
    )
