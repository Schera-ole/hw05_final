from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from .models import Post, Group, User, Comment, Follow
from .forms import PostForm, CommentForm
from django.contrib.auth.decorators import login_required
import datetime as dt
from django.urls import reverse

# Create your views here


def index(request):
    post_list = Post.objects.prefetch_related("author").order_by("-pub_date").all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return render(request, "index.html", {"page": page, "paginator": paginator})


@login_required
def follow_index(request):
    follow = Follow.objects.select_related("author", "user").filter(user=request.user)
    author_list = [favorite.author for favorite in follow]
    post_list = Post.objects.filter(author__in=author_list).order_by("-pub_date")
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return render(request, "follow.html", {"page": page, "paginator": paginator})


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = (
        Post.objects.prefetch_related("author", "group")
        .filter(group=group)
        .order_by("-pub_date")[:12]
    )
    paginator = Paginator(posts, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return render(
        request, "group.html", {"group": group, "page": page, "paginator": paginator}
    )


@login_required
def new_post(request):
    if request.method == "POST":
        form = PostForm(request.POST or None, files=request.FILES or None)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect("index")
        return render(request, "new.html", {"form": form})
    form = PostForm()
    return render(request, "new.html", {"form": form})


def profile(request, username):
    # тут тело функции
    user_profile = get_object_or_404(User, username=username)
    post_all = (
        Post.objects.prefetch_related("author")
        .filter(author=user_profile)
        .order_by("-pub_date")
    )
    paginator = Paginator(post_all, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    if request.user.is_authenticated:
        if Follow.objects.filter(user=request.user, author=user_profile).count() > 0:
            following = True
            return render(
                request,
                "profile.html",
                {
                    "user_profile": user_profile,
                    "post_all": post_all,
                    "paginator": paginator,
                    "page": page,
                    "following": following,
                },
            )
    return render(
        request,
        "profile.html",
        {
            "user_profile": user_profile,
            "post_all": post_all,
            "paginator": paginator,
            "page": page,
        },
    )


def post_view(request, username, post_id):
    # тут тело функции
    user_profile = get_object_or_404(User, username=username)
    post_count = (
        Post.objects.prefetch_related("author").filter(author=user_profile).count()
    )
    post = Post.objects.get(pk=post_id)
    form = CommentForm()
    comments = Comment.objects.filter(post=post_id).order_by("-created")
    return render(
        request,
        "post.html",
        {
            "user_profile": user_profile,
            "post": post,
            "post_count": post_count,
            "form": form,
            "comments": comments,
        },
    )


@login_required
def add_comment(request, username, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            comment.save()
            return redirect("post", username=post.author.username, post_id=post_id)
    form = CommentForm()
    return redirect("post", username=post.author.username, post_id=post_id)


def post_edit(request, username, post_id):
    # тут тело функции. Не забудьте проверить,
    # что текущий пользователь — это автор записи.
    # В качестве шаблона используйте шаблон для создания новой записи,
    # который вы использовали раньше (вы могли назвать шаблон иначе)
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect(
            reverse("post", kwargs={"username": username, "post_id": post_id})
        )
    if request.method == "POST":
        form = PostForm(
            request.POST or None, files=request.FILES or None, instance=post
        )
        if form.is_valid():
            post.save()
        return redirect(
            reverse("post", kwargs={"username": username, "post_id": post_id})
        )
    else:
        form = PostForm(
            request.POST or None, files=request.FILES or None, instance=post
        )
    return render(request, "edit.html", {"form": form, "post": post})


def page_not_found(request, exception):
    # Переменная exception содержит отладочную информацию,
    # выводить её в шаблон пользователской страницы 404 мы не станем
    return render(request, "misc/404.html", {"path": request.path}, status=404)


def server_error(request):
    return render(request, "misc/500.html", status=500)


@login_required
def profile_follow(request, username):
    if request.user.username != username:
        follower = User.objects.get(username=request.user.username)
        following = User.objects.get(username=username)
        if Follow.objects.filter(user=follower, author=following).count() == 0:
            Follow.objects.create(user=follower, author=following)
            return redirect("profile", username=username)
    return redirect("profile", username=username)


@login_required
def profile_unfollow(request, username):
    follower = User.objects.get(username=request.user.username)
    following = User.objects.get(username=username)
    Follow.objects.filter(user=follower, author=following).delete()
    return redirect("profile", username=username)
