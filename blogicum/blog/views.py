from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import CommentForm, PostForm, ProfileEditForm
from .mixins import (
    BasePostMixin,
    CommentBaseMixin,
    CommentObjectMixin,
    OwnerRequiredMixin,
)
from .models import Category, Post, User

PAGINATE_BY = 10


def get_published_posts(queryset):
    """Фильтрация только опубликованных постов."""
    return queryset.filter(
        is_published=True,
        pub_date__lte=timezone.now()
    ).filter(
        Q(category__isnull=True) | Q(category__is_published=True)
    )


def annotate_comment_count(queryset):
    """Аннотация количества комментариев и сортировка."""
    return queryset.annotate(
        comment_count=Count('comments')
    ).order_by(*Post._meta.ordering)


def paginate_posts(request, queryset, per_page):
    """Пагинация."""
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


class PostListView(ListView):
    """Список всех опубликованных постов."""

    model = Post
    template_name = 'blog/index.html'
    context_object_name = 'post_list'
    
    def get_queryset(self):
        qs = Post.objects.select_related('category', 'location', 'author')
        qs = get_published_posts(qs)
        return annotate_comment_count(qs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_obj'] = paginate_posts(self.request, self.get_queryset(), PAGINATE_BY)
        return context


class CategoryPostsView(ListView):
    """Отображение постов в категории."""

    model = Post
    template_name = 'blog/category.html'
    context_object_name = 'post_list'
    paginate_by = PAGINATE_BY

    def get_category(self):
        return get_object_or_404(
            Category, slug=self.kwargs['category_slug'], is_published=True
        )

    def get_queryset(self):
        qs = self.get_category().posts.select_related(
            'category', 'location', 'author'
        )
        qs = get_published_posts(qs)
        return annotate_comment_count(qs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.get_category()
        context['page_obj'] = paginate_posts(self.request, self.get_queryset(), PAGINATE_BY)
        return context


class PostDetailView(BasePostMixin, DetailView):
    """Детали поста."""

    template_name = 'blog/detail.html'
    pk_url_kwarg = 'post_id'

    def get_object(self):
        post = super().get_object()
        if self.request.user == post.author:
            return post
        qs = get_published_posts(Post.objects.all())
        return get_object_or_404(qs, pk=self.kwargs.get(self.pk_url_kwarg))

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **kwargs,
            form=CommentForm(),
            comments=self.get_object().comments.select_related('author')
        )


class PostCreateView(BasePostMixin, LoginRequiredMixin, CreateView):
    """Создание нового поста."""

    form_class = PostForm
    template_name = 'blog/create.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('blog:profile', args=[self.request.user.username])


class PostUpdateView(BasePostMixin, OwnerRequiredMixin, UpdateView):
    """Редактирование поста."""

    pk_url_kwarg = 'post_id'
    form_class = PostForm
    template_name = 'blog/create.html'

    def get_success_url(self):
        return reverse('blog:post_detail',
                       args=[self.kwargs[self.pk_url_kwarg]])


class PostDeleteView(BasePostMixin, LoginRequiredMixin,
                     OwnerRequiredMixin, DeleteView):
    """Удаление поста."""
    template_name = 'blog/post_confirm_delete.html'

    def get_success_url(self):
        return reverse('blog:profile', args=[self.request.user.username])


class ProfileView(ListView):
    """Профиль пользователя."""

    template_name = 'blog/profile.html'

    def get_author(self):
        return get_object_or_404(User, username=self.kwargs['username'])

    def get_queryset(self):
        author = self.get_author()
        qs = author.posts.select_related('category', 'location', 'author')

        if self.request.user != author:
            qs = get_published_posts(qs)

        return annotate_comment_count(qs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.get_author()
        context['is_owner'] = self.request.user == self.get_author()
        context['page_obj'] = paginate_posts(
            self.request, self.get_queryset(), PAGINATE_BY
        )
        return context


class ProfileEditView(LoginRequiredMixin, UpdateView):
    """Редактирование профиля."""

    model = User
    template_name = 'blog/user.html'
    form_class = ProfileEditForm

    def get_object(self):
        return self.request.user

    def get_success_url(self):
        return reverse('blog:profile', args=[self.request.user.username])


class CommentCreateView(CommentBaseMixin, CreateView):
    """Создание комментария к посту."""

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.post = get_object_or_404(Post, pk=self.kwargs['post_id'])
        return super().form_valid(form)


class CommentUpdateView(CommentBaseMixin, OwnerRequiredMixin,
                        CommentObjectMixin, UpdateView):
    """Редактирование комментария."""


class CommentDeleteView(LoginRequiredMixin, OwnerRequiredMixin,
                        CommentObjectMixin, DeleteView):
    """Удаление комментария."""
    template_name = 'blog/comment_confirm_delete.html'
