from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, DeleteView, UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.models import User
from .models import Post, Category, BlogImage
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.core.paginator import EmptyPage
from django.db.models import Q
from .forms import SearchForm
from .forms import PostForm
import time
from PIL import Image
from django.contrib.auth.decorators import login_required
from .models import Post, Like, Dislike, Comment

def intro(request):
    return render(request, 'blog/intro.html')

def home(request):
    context = {
        'posts':Post.objects.all()
    }
    return render(request,'blog/home.html', context)

class PostListView(ListView):
    model = Post
    template_name = 'blog/home.html' #app/model_viewtype.html
    context_object_name = 'posts'
    ordering = ['-date_posted']
    paginate_by = 6
    
    def get_queryset(self):
        queryset = super().get_queryset()
        for post in queryset:
            print(post.id)  
        return queryset


    
class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/post_form.html'
    success_url = reverse_lazy('blog-home')

    def form_valid(self, form):
        form.instance.author = self.request.user
        post = form.save()
        
        images = self.request.FILES.getlist('images')
        # `images` should match the input field name in your form

        # Check if new_category is filled
        new_category = form.cleaned_data.get('new_category')
        if new_category:
            # Create the category if it doesn't exist
            category, created = Category.objects.get_or_create(name=new_category)
            form.instance.category = category
            post = form.save()
            
        for image_file in images:
            blog_image = BlogImage.objects.create(post=post, image=image_file)
            image = Image.open(blog_image.image)
            
            output_size = (500, 500)  # desired width and height
            image.thumbnail(output_size)
            
            image.save(blog_image.image.path, quality=85)

        return super().form_valid(form)
    

class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    fields = ['title', 'content', 'category', 'image']

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def test_func(self):
        post = self.get_object()
        if self.request.user == post.author:
            return True
        return False

class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    template_name = 'blog/post_confirm_delete.html'
    success_url = reverse_lazy('blog-home')

    def test_func(self):
        post = self.get_object()
        if self.request.user == post.author:
            return True
        return False
    



def search_view(request):
    queryset = Post.objects.all()
    query = request.GET.get('query', '')  # Default to an empty string if 'query' doesn't exist
    template_name = 'blog/search_results.html'

    if query:
        category = Category.objects.filter(name__iexact=query).first()
        if category:
            queryset = Post.objects.filter(category=category)
        else:
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query)
            )

    context = {
        'results': queryset,  # renaming 'queryset' to 'results' to match your template
        'query': query
    }

    return render(request, template_name, context)





def form_valid(self, form):
    form.instance.author = self.request.user
    return super().form_valid(form)

    
def about(request):
    return render(request, 'blog/about.html', {"title" : "About"})

def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    return render(request, 'blog/post_detail.html', {'post': post})

def get_paginated_posts(request):
    page = request.GET.get('page', 1)
    posts = Post.objects.all().order_by('-date_posted')
    paginator = Paginator(posts, 6)
    
    try:
        current_page = paginator.page(page)
    except EmptyPage:
        return JsonResponse([], safe=False)  # Return empty list when no more data

    serialized_data = [
        {
            'id': post.id,
            'title': post.title,
            'author': post.author.username if post.author else "Bloga🖊📝",
            'content': post.content,
            'date_posted': post.date_posted.strftime('%Y-%m-%d %H:%M:%S'),
            'image': post.image.url if post.image else None,
            'teaser': post.teaser(),
            'image_url': post.get_image_url(),

        }
        for post in current_page
    ]

    return JsonResponse(serialized_data, safe=False)


    

def users_profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    context = {
        'profile_user': profile_user
    }
    return render(request, 'blog/profile.html', {'profile_user': profile_user})


@login_required
def like_post(request):
    post_id = request.POST.get('post_id')
    post = get_object_or_404(Post, id=post_id)
    if post.likes.filter(id=request.user.id).exists():
        # User already liked this post. Remove like.
        post.likes.remove(request.user)
        is_liked = False
    else:
        # User hasn't liked this post yet. Add like.
        post.likes.add(request.user)
        is_liked = True
    return JsonResponse({'isLiked': is_liked, 'totalLikes': post.likes.count()}, safe=False)

@login_required
def dislike_post(request):
    post_id = request.POST.get('post_id')
    post = get_object_or_404(Post, id=post_id)
    if post.dislikes.filter(id=request.user.id).exists():
        # User already disliked this post. Remove dislike.
        post.dislikes.remove(request.user)
        is_disliked = False
    else:
        # User hasn't disliked this post yet. Add dislike.
        post.dislikes.add(request.user)
        is_disliked = True
    return JsonResponse({'isDisliked': is_disliked, 'totalDislikes': post.dislikes.count()}, safe=False)

@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == 'POST':
        text = request.POST.get('text')
        comment = Comment.objects.create(post=post, user=request.user, text=text)
        comment.save()
        return redirect('blog-home')
    return render(request, 'blog/add_comment.html', {'post': post})
