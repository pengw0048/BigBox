from django import forms

namepattern = r"^\w+$"
textpattern = r"^[a-zA-Z\.\- ]+$"
textwidget = forms.TextInput(attrs={"class": "form-control"})
passwidget = forms.PasswordInput(attrs={"class": "form-control"})
emailwidget = forms.EmailInput(attrs={"class": "form-control"})


class LoginForm(forms.Form):
    username = forms.RegexField(namepattern, 30, 1, widget=textwidget)
    password = forms.RegexField(namepattern, 30, 1, widget=passwidget)


class RegisterForm(forms.Form):
    first_name = forms.RegexField(textpattern, 30, 1, widget=textwidget)
    last_name = forms.RegexField(textpattern, 30, 1, widget=textwidget)
    email = forms.EmailField(widget=emailwidget)
    username = forms.RegexField(namepattern, 30, 1, widget=textwidget, label='Username (letters and digits)')
    password = forms.RegexField(namepattern, 30, 1, widget=passwidget, label='Password (letters and digits)')
    password_confirm = forms.RegexField(namepattern, 30, 1, widget=passwidget, label='Password again')

    def clean(self):
        cleaned_data = super(RegisterForm, self).clean()
        if cleaned_data.get('password') != cleaned_data.get('password_confirm'):
            raise forms.ValidationError('Passwords not match')
