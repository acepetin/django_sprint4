from django.shortcuts import render
from .models import Post, Category
from datetime import datetime
from django.shortcuts import get_object_or_404
# Create your views here.


posts = Post.objects.all()


def post_filter(posts):
    filter_posts = posts.filter(is_published=True,
                                category__is_published=True,
                                pub_date__date__lte=datetime.now()
                                )
    return filter_posts


def index(request):
    template = 'blog/index.html'
    context = {'post_list': post_filter(posts).order_by('-pub_date')[:5]}
    return render(request, template, context)


def post_detail(request, id):
    template = 'blog/detail.html'
    post = get_object_or_404(post_filter(posts),
                             id=id)
    context = {'post': post}
    return render(request, template, context)


def category_posts(request, category_slug):
    template = 'blog/category.html'
    category_slug = get_object_or_404(Category.objects.filter(
        is_published=True), slug=category_slug)
    context = {'category': category_slug,
               'post_list': post_filter(posts).filter(category=category_slug)}
    return render(request, template, context)
