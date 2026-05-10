#!/usr/bin/env python
"""
Create sample blog posts for testing
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "siteproject.settings")
django.setup()

from siteapp.models import BlogPost
from django.utils.text import slugify

# Check if posts already exist
existing_count = BlogPost.objects.count()
print(f"Existing blog posts: {existing_count}")

if existing_count == 0:
    # Create sample blog posts
    posts_data = [
        {
            "title": "Getting Started with Python Programming",
            "content": "Python is one of the most beginner-friendly programming languages. Learn the basics of Python including variables, data types, loops, and functions. Python's simple syntax makes it perfect for newcomers to programming. In this comprehensive guide, we'll cover everything you need to know to start your Python journey. From setting up your environment to writing your first program, we'll walk you through each step. Python is widely used in web development, data science, artificial intelligence, and automation. Start coding today and unlock endless possibilities!",
        },
        {
            "title": "Web Development with Django Framework",
            "content": "Django is a powerful Python web framework that simplifies web development. Learn how to build robust, scalable web applications using Django's batteries-included approach. Django provides built-in solutions for authentication, database management, admin panel, and much more. In this tutorial, we explore Django's architecture, models, views, and templates. Discover how to create RESTful APIs, handle user authentication, and deploy your applications. Whether you're building a simple blog or a complex enterprise application, Django has you covered.",
        },
        {
            "title": "Mastering Data Structures and Algorithms",
            "content": "Understanding data structures and algorithms is crucial for every programmer. Learn about arrays, linked lists, stacks, queues, trees, and graphs. Discover sorting algorithms like quick sort, merge sort, and heap sort. Master searching algorithms including binary search and depth-first search. Algorithm complexity analysis helps you write efficient code. Problem-solving techniques and common patterns are essential for coding interviews. This comprehensive guide prepares you for technical challenges ahead.",
        },
        {
            "title": "Introduction to Machine Learning",
            "content": "Machine learning is transforming industries and creating new opportunities for developers. Start with the fundamentals of supervised and unsupervised learning. Learn about classification, regression, and clustering techniques. Understand popular libraries like scikit-learn, TensorFlow, and PyTorch. Build your first machine learning model and deploy it in production. Discover real-world applications in computer vision, natural language processing, and recommendation systems. Begin your machine learning journey today!",
        },
        {
            "title": "Clean Code Best Practices",
            "content": "Writing clean, maintainable code is an art that every developer should master. Learn naming conventions, code organization, and documentation practices. Understand the principles of DRY (Don't Repeat Yourself) and SOLID. Discover refactoring techniques that improve code quality. Code reviews and testing are integral to maintaining clean code. Explore design patterns that solve common programming problems. Clean code leads to fewer bugs, easier maintenance, and happier teams.",
        },
    ]

    for data in posts_data:
        slug = slugify(data["title"])
        post, created = BlogPost.objects.get_or_create(
            slug=slug,
            defaults={
                "title": data["title"],
                "content": data["content"],
            },
        )
        if created:
            print(f"✓ Created: {post.title}")
        else:
            print(f"→ Already exists: {post.title}")

    print(f"\nTotal blog posts: {BlogPost.objects.count()}")
else:
    print(f"Blog posts already exist in the database: {existing_count}")
    for post in BlogPost.objects.all()[:5]:
        print(f"  - {post.title}")
