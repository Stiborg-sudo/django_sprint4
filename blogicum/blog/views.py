from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    CommentForm,
    PostForm,
    RegistrationForm,
    UserEditForm,
)
from .models import Category, Comment, Post


User = get_user_model()

POSTS_PER_PAGE = 10


def get_published_posts(posts=None):
    if posts is None:
        posts = Post.objects

    return posts.filter(
        is_published=True,
        pub_date__lte=timezone.now(),
        category__is_published=True,
    ).select_related(
        'author',
        'location',
        'category',
    ).annotate(
        comment_count=Count('comments')
    ).order_by('-pub_date')


def paginate_posts(request, posts):
    paginator = Paginator(posts, POSTS_PER_PAGE)
    return paginator.get_page(request.GET.get('page'))


def index(request):
    page_obj = paginate_posts(request, get_published_posts())

    return render(
        request,
        'blog/index.html',
        {
            'page_obj': page_obj,
            'post_list': page_obj.object_list,
        }
    )


def post_detail(request, id):
    posts = Post.objects.select_related(
        'author',
        'location',
        'category',
    ).annotate(
        comment_count=Count('comments')
    )

    if request.user.is_authenticated:
        posts = posts.filter(
            Q(
                is_published=True,
                pub_date__lte=timezone.now(),
                category__is_published=True,
            ) | Q(author=request.user)
        )
    else:
        posts = posts.filter(
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True,
        )

    post = get_object_or_404(posts, pk=id)

    return render(
        request,
        'blog/detail.html',
        {
            'post': post,
            'comments': post.comments.select_related('author'),
            'form': CommentForm(),
        }
    )


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True,
    )

    posts = get_published_posts(category.posts.all())
    page_obj = paginate_posts(request, posts)

    return render(
        request,
        'blog/category.html',
        {
            'category': category,
            'page_obj': page_obj,
            'post_list': page_obj.object_list,
        }
    )


def profile(request, username):
    profile = get_object_or_404(User, username=username)

    posts = profile.posts.select_related(
        'author',
        'location',
        'category',
    ).annotate(
        comment_count=Count('comments')
    )

    if request.user != profile:
        posts = get_published_posts(posts)

    page_obj = paginate_posts(
        request,
        posts.order_by('-pub_date')
    )

    return render(
        request,
        'blog/profile.html',
        {
            'profile': profile,
            'page_obj': page_obj,
        }
    )


@login_required
def create_post(request):
    form = PostForm(
        request.POST or None,
        request.FILES or None
    )

    if request.method == 'POST' and form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect(
            'blog:profile',
            username=request.user.username
        )

    return render(request, 'blog/create.html', {'form': form})


@login_required
def edit_post(request, id):
    post = get_object_or_404(Post, pk=id)

    if post.author != request.user:
        return redirect('blog:post_detail', id=id)

    form = PostForm(
        request.POST or None,
        request.FILES or None,
        instance=post
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('blog:post_detail', id=id)

    return render(request, 'blog/create.html', {'form': form})


@login_required
def delete_post(request, id):
    post = get_object_or_404(Post, pk=id)

    if post.author != request.user:
        return redirect('blog:post_detail', id=id)

    form = PostForm(instance=post)

    if request.method == 'POST':
        post.delete()
        return redirect(
            'blog:profile',
            username=request.user.username
        )

    return render(request, 'blog/create.html', {'form': form})


@login_required
def add_comment(request, id):
    post = get_object_or_404(get_published_posts(), pk=id)

    form = CommentForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()

    return redirect('blog:post_detail', id=id)


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(
        Comment,
        pk=comment_id,
        post_id=post_id
    )

    if comment.author != request.user:
        return redirect('blog:post_detail', id=post_id)

    form = CommentForm(
        request.POST or None,
        instance=comment
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('blog:post_detail', id=post_id)

    return render(
        request,
        'blog/comment.html',
        {
            'form': form,
            'comment': comment,
        }
    )


@login_required
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(
        Comment,
        pk=comment_id,
        post_id=post_id
    )

    if comment.author != request.user:
        return redirect('blog:post_detail', id=post_id)

    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', id=post_id)

    return render(
        request,
        'blog/comment.html',
        {
            'comment': comment,
        }
    )


@login_required
def edit_profile(request):
    form = UserEditForm(
        request.POST or None,
        instance=request.user
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect(
            'blog:profile',
            username=request.user.username
        )

    return render(request, 'blog/user.html', {'form': form})


def registration(request):
    form = RegistrationForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('login')

    return render(
        request,
        'registration/registration_form.html',
        {'form': form}
    )
