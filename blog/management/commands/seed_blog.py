from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from blog.models import Category, Post, Tag

User = get_user_model()

POSTS = [
    {
        "title": "Ship a Django API that people can actually pay for",
        "excerpt": "Chapa, JWT, and the boring operations that turn a school project into a product.",
        "content": """Most Django portfolios stop at CRUD. Money starts when a real shop or school can log in, pay, and come back tomorrow.

## What to productize

- Attendance reports parents already ask for
- Telegram-first checkout, not a fake Amazon
- Draft → published workflow so staff can review before the public sees it

Keep the domain language in Amharic where the user is. English APIs are fine; English-only screens are not.
""",
        "cats": ["Engineering"],
        "tags": ["django", "ethiopia", "product"],
        "featured": True,
    },
    {
        "title": "Why ECB DES is a teaching tool, not a vault",
        "excerpt": "56-bit keys, no IV, no MAC. The upgrade path is Triple DES plus HMAC — or just use AES-GCM.",
        "content": """If your cipher prints ciphertext as Python `chr()` soup, you do not have encryption. You have a demo.

Wrap a correct Feistel engine in:

1. CBC or CTR with a random IV
2. PBKDF2 for passwords
3. Encrypt-then-MAC

Then write the FIPS test vector in `self_test()`. That is the difference between a homework file and a repository you can defend in an interview.
""",
        "cats": ["Security"],
        "tags": ["crypto", "des"],
        "featured": False,
    },
    {
        "title": "Notes from Addis: build for Telegram, not for the App Store first",
        "excerpt": "Distribution is the product. Meet sellers where they already close deals.",
        "content": """A clothing seller in Piassa will not install your PWA. They will paste a payment link into Telegram.

So the first version of a shop system is:

- catalog
- stock count
- paid / not paid
- a photo of the receipt

Charge a setup fee. Collect the monthly fee in Telebirr. Expand later.
""",
        "cats": ["Business"],
        "tags": ["ethiopia", "telegram"],
        "featured": False,
    },
]


class Command(BaseCommand):
    help = "Create a demo author, categories, tags, and published posts."

    def handle(self, *args, **options):
        extra = {}
        if "name" in {f.name for f in User._meta.get_fields()}:
            extra["name"] = "Hgus"
        user, created = User.objects.get_or_create(
            username="hgus",
            defaults={"email": "hgus@example.com", **extra},
        )
        if created or not user.has_usable_password():
            user.set_password("ledger12345")
            if extra:
                user.name = extra["name"]
            user.save()
        elif extra and not getattr(user, "name", None):
            user.name = extra["name"]
            user.save(update_fields=["name"])

        cat_map = {}
        for name in ["Engineering", "Security", "Business"]:
            cat_map[name], _ = Category.objects.get_or_create(name=name)

        for spec in POSTS:
            post, made = Post.objects.update_or_create(
                title=spec["title"],
                defaults={
                    "author": user,
                    "excerpt": spec["excerpt"],
                    "content": spec["content"],
                    "status": Post.Status.PUBLISHED,
                    "featured": spec["featured"],
                    "published_at": timezone.now(),
                    "is_deleted": False,
                },
            )
            post.categories.set([cat_map[n] for n in spec["cats"]])
            tags = []
            for t in spec["tags"]:
                tag, _ = Tag.objects.get_or_create(name=t)
                tags.append(tag)
            post.tags.set(tags)

        self.stdout.write(self.style.SUCCESS("Seeded Ledger. Login: hgus / ledger12345"))
