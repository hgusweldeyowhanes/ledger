from django import forms
from django.contrib.auth import get_user_model

from .models import Comment, NewsletterSubscriber, Post, Series

User = get_user_model()


class PostForm(forms.ModelForm):
    tag_names = forms.CharField(
        required=False,
        help_text="Comma-separated tags",
        widget=forms.TextInput(attrs={"placeholder": "django, ethiopia, backend"}),
    )
    series = forms.ModelChoiceField(
        queryset=Series.objects.none(),
        required=False,
        empty_label="No series",
    )
    series_position = forms.IntegerField(required=False, min_value=1, initial=1)

    class Meta:
        model = Post
        fields = (
            "title",
            "excerpt",
            "content",
            "cover_image",
            "categories",
            "status",
            "featured",
            "allow_comments",
            "published_at",
        )
        widgets = {
            "excerpt": forms.Textarea(attrs={"rows": 2}),
            "content": forms.Textarea(attrs={"rows": 16}),
            "published_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["series"].queryset = Series.objects.filter(author=user)
        elif self.instance and self.instance.pk:
            self.fields["series"].queryset = Series.objects.filter(author=self.instance.author)


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("body",)
        widgets = {
            "body": forms.Textarea(attrs={"rows": 3, "placeholder": "Write a reply…"}),
        }


class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("password2"):
            self.add_error("password2", "Passwords must match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        if hasattr(user, "name"):
            user.name = self.cleaned_data.get("first_name") or self.cleaned_data["username"]
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class NewsletterForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = ("email",)
        widgets = {
            "email": forms.EmailInput(attrs={"placeholder": "you@example.com"}),
        }


class SeriesForm(forms.ModelForm):
    class Meta:
        model = Series
        fields = ("title", "description", "cover_image")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }
