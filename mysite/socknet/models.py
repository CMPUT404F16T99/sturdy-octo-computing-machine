from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from socknet.utils import HTMLsafe, AuthorInfo
from django.contrib.postgres.fields import ArrayField
# for images auto delete
from django.db.models.signals import pre_delete
from django.dispatch import receiver
import uuid
from itertools import chain
from socknet.utils import is_FOAF_local

class Node(models.Model):
    """
    Represents a server we can communicate with
    """
    name = models.CharField(max_length=32) # A name for a host. (Ex) socknet
    url = models.URLField(unique=True)
    # user to use for node to use this account as basicauth.
    foreignUserAccessAccount = models.OneToOneField(User)
    # String UserID and Password to access foreign node via basic auth
    foreignNodeUser = models.CharField(max_length=256, null=True)
    foreignNodePass = models.CharField(max_length=256, null=True)

    def __str__(self):
        return self.name

class ForeignAuthor(models.Model):
    """
    Represents an author from another node
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Store display name because its needed in lots of places, update it whenever we grab the profile.
    display_name=models.CharField(max_length=150, default='test')
    node = models.ForeignKey(Node, related_name="my_node")
    url = models.URLField(default='')
    #host = models.URLField(default ='')

    def __str__(self):
        return self.display_name

class Author(models.Model):
    """
    Represents an author

    Friends, followers, and friend Requests need to be designed such that:
    - Querying for friends or followers is quick
    - Friends of friends is easy to compute
    - It is easy to decline friend requests
    - Querying pending friend requests is quick
    """
    user = models.OneToOneField(User)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)

    # Friends and followers are separate --> I can be both a friend and a follower
    # ignored is for friend requests you have declined, just means it won't show up as pending
    friends = models.ManyToManyField("self", related_name="my_friends", blank=True)
    who_im_following = models.ManyToManyField("self", related_name="my_followers", symmetrical=False, blank=True)
    ignored = models.ManyToManyField("self", related_name="ignored_by", symmetrical=False, blank=True)

    # Friend stuff for forgein authors
    foreign_friends = models.ManyToManyField(ForeignAuthor, related_name="my_foreign_friends", blank=True)
    pending_foreign_friends = models.ManyToManyField(ForeignAuthor, related_name="my_pending_foreign_friend_requests", blank=True)
    foreign_friends_im_following = models.ManyToManyField(ForeignAuthor, related_name="foreign_friends_im_following", blank=True)

    # Profile fields
    github_url = models.URLField(blank=True)
    about_me = models.CharField(max_length=1000, blank=True)
    birthday = models.DateField(null=True,blank=True)
    displayName = models.CharField(max_length=150, blank=True)
    url = models.URLField(blank=True)
    host = models.URLField(default='')

    def __str__(self):
        return self.user.get_username()

    def get_site(self):
        # Get the url for the author
        return Site.objects.get_current().domain


    def is_friend(self, author_uuid):
        """
        Checks if an author is this author's friend.
        Checks both local and foreign friend lists.
        """
        is_friend = self.friends.filter(uuid=author_uuid).exists()
        if not is_friend:
            # If author is not a local friend, check if they are a foreign friend
            is_friend = self.foreign_friends.filter(id=author_uuid).exists()
        return is_friend

    def get_pending_local_friend_requests(self):
        """
        Returns all pending local authors
        """
        local_pending = self.my_followers.all()
        local_pending = local_pending.exclude(pk__in=self.ignored.all()) # ignored requests we have declined
        local_pending = local_pending.exclude(pk__in=self.friends.all()) # ignored people we are already friends with
        return local_pending

    def get_pending_friend_requests(self):
        """
        Returns an array of AuthorInfo objects containing the pending friend request information (both local and foreign authors)
        """
        all_pending = []
        local_pending = self.get_pending_local_friend_requests()
        for author in local_pending:
            all_pending.append(AuthorInfo(author.displayName, "Local", author.uuid, True))
        for author in self.pending_foreign_friends.all():
            all_pending.append(AuthorInfo(author.display_name, author.node.name, author.id, False))
        all_pending.sort(key=lambda x: x.name.lower())
        return all_pending

    def get_friends(self):
        """
        Returns an array of AuthorInfo objects containing the all friend information (both local and foreign authors)
        """
        all_friends = []
        for author in self.friends.all():
            # Local friends
            all_friends.append(AuthorInfo(author.displayName, "Local", author.uuid, True))
        for author in self.foreign_friends.all():
            all_friends.append(AuthorInfo(author.display_name, author.node.name, author.id, False))
        all_friends.sort(key=lambda x: x.name.lower())
        return all_friends

    def get_friend_models(self):
        return self.friends

    def get_pending_friend_request_count(self):
        return len(self.get_pending_friend_requests())

    def accept_friend_request(self, requester_uuid, is_local):
        """
        Local behaviour: When a friend request is accepted,
        both authors will be considered followers AND friends of each other.
        """
        if is_local:
            requester = Author.objects.get(uuid=requester_uuid)
            if requester not in self.my_followers.all():
                # Stale state, should probably reload the page
                raise ValueError("Attempted to accept friend request when requester is no longer following me!")
            if requester not in self.friends.all():
                self.friends.add(requester)
            if requester not in self.who_im_following.all():
                self.who_im_following.add(requester)
            if requester in self.ignored.all():
                # If we had them ignored previously, we are friends now
                self.ignored.remove(requester)
        else:
            requester = ForeignAuthor.objects.get(id=requester_uuid)
            if requester not in self.foreign_friends.all():
                self.foreign_friends.add(requester)
            if requester in self.pending_foreign_friends.all():
                self.pending_foreign_friends.remove(requester)
            if requester in self.foreign_friends_im_following.all():
                # Incase the other group does something weird..
                self.foreign_friends_im_following.remove(requester)
        self.save()
        return

    def decline_friend_request(self, requester_uuid, is_local):
        """
        Local behaviour: When we decline a friend request we simply move the requester into
        our ignored queue (all this means is it won't show up in our friend requests).
        Foreign behaviour: Delete from pending foreign friend requests.
        """
        if is_local:
            requester = Author.objects.get(uuid=requester_uuid)
            self.ignored.add(requester)
        else:
            requester = ForeignAuthor.objects.get(id=requester_uuid)
            self.pending_foreign_friends.remove(requester)
        self.save()
        return

    def delete_friend(self, friend, is_local):
        """
        Deletes both local and foreign friends.
        Local: When we remove a friend, we unfriend and unfollow them.
        """
        if is_local:
            # Remove a local friend
            self.friends.remove(friend)
            self.who_im_following.remove(friend)
        else:
            # Remove a foreign friend
            self.foreign_friends.remove(friend)
        self.save()
        return

    def follow(self, friend):
        # Local authors only
        self.who_im_following.add(friend)
        if friend in self.ignored.all():
            # If we had them ignored previously, we are following them now
            self.ignored.remove(friend)
        self.save()

    def unfollow(self, friend):
        # Local authors only
        self.who_im_following.remove(friend)
        self.save()

    def get_following_only(self):
        """ Get who I am following excluding friends (local only)"""
        following = self.who_im_following.all()
        following = following.exclude(pk__in=self.friends.all())
        return following

    def get_all_friend_uuids(self):
        """
        Returns a list all of the authors local and foreign friend uuids.
        """
        local_uuids = [friend.uuid for friend in self.friends.all()]
        foreign_uuids = [friend.id for friend in self.foreign_friends.all()]
        return local_uuids + foreign_uuids

class Post(models.Model):
    """ Represents a post made by a user """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(Author, related_name="author")
    title = models.CharField(max_length=64, default="No Title")
    description = models.CharField(max_length=128, default="No description provided.")
    content = models.TextField(max_length=512)
    created_on = models.DateTimeField(auto_now=True)
    markdown = models.BooleanField()
    #imglink = models.CharField(max_length=256)
    imglink = models.UUIDField(editable=True, null=True)
    visibility = models.CharField(default='PUBLIC', max_length=255, choices=[
        ('PUBLIC', 'PUBLIC'),
        ('FOAF', 'FOAF'),
        ('FRIENDS', 'FRIENDS'),
        ('PRIVATE', 'PRIVATE'),
        ('SERVERONLY', 'SERVERONLY')])
    # TODO: Change to an ArrayField
    categories = models.CharField(default="N/A", max_length=64, blank=True)

    def get_absolute_url(self):
        """ Gets the canonical URL for a Post
        Will be of the format .../posts/<id>/
        """
        return reverse('view_post', args=[str(self.id)])

    def view_content(self):
        """ Retrieves content to be displayed as html, it is assumed safe
        due to HTMLsafe's get_converted_content() applies HTML escapes already.
        """
        return HTMLsafe.get_converted_content(self.markdown, self.content)

    def getFullEnglishVisibility(self):
        ''' Gets the full, written out English phrase
        for the visibility string'''
        if (self.visibility == 'PUBLIC'):
            return 'Public'
        elif (self.visibility == 'FOAF'):
            return 'Friend of Friends'
        elif (self.visibility == 'FRIENDS'):
            return 'Friends'
        elif (self.visibility == 'PRIVATE'):
            return 'Private'
        elif (self.visibility == 'SERVERONLY'):
            return 'Server Friends'
        else:
            return 'Unknown'

    # enable weird characters like lenny faces taken from:
    #http://stackoverflow.com/questions/36389723/why-is-django-using-ascii-instead-of-utf-8
    def __unicode__(self):
        return self.author.displayName + ": " + self.content

class PostManager(models.Model):

    def get_local_profile_posts(self, profile_author, current_author):
        """
        Returns the posts to display when viewing someone's profile.
        This is for local profiles only.
        """
        # If someone is viewing their own page, they can see all posts
        if profile_author == current_author:
            return Post.objects.filter(author=profile_author).order_by('-created_on')

        public_posts = Post.objects.filter(author=profile_author, visibility='PUBLIC')
        friend_posts = {}
        foaf_posts = {}
        server_friends_posts = {}

        if current_author in profile_author.friends.all():
            # If we are friends, then I can see FRIENDS, FOAF, and SERVERONLY
            friend_posts = Post.objects.filter(author=profile_author, visibility='FRIENDS')
            foaf_posts = Post.objects.filter(author=profile_author, visibility="FOAF")
            server_friends_posts = Post.objects.filter(author=profile_author, visibility="SERVERONLY")
        elif is_FOAF_local(current_author, profile_author):
            # If I am a FOAF, then I can only see FRIENDS
            foaf_posts = Post.objects.filter(author=profile_author, visibility="FOAF")

        # Combine the query sets, sort by most recent
        visible_posts = sorted(
            chain(public_posts, friend_posts, foaf_posts, server_friends_posts),
            key=lambda instance: instance.created_on, reverse=True)

        return visible_posts

class CommentQuerySet(models.QuerySet):
    """ Query operations for the Comments table. """
    def all_comments_for_post(self, post_pk, ordered):
        # Retrieve only post specific comments
        results = self.filter(parent_post_id=post_pk)
        # Order it with latest date on top
        if(ordered):
            results = results.order_by('-created_on',)
        return results

    def comments_count_post(self, post_pk):
        result = self.filter(parent_post_id=post_pk).count()
        return results

    def all_comments_for_author(self, author_pk, ordered):
        # Retrieve only post specific comments
        results = self.filter(author_id=author_pk)
        # Order it with latest date on top
        if(ordered):
            results = results.order_by('-created_on',)
        return results

class Comment(models.Model):
    """ Represents a comment made by a user """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    objects = CommentQuerySet.as_manager()
    # Should really use model inheritance, found out about it too late though, https://docs.djangoproject.com/en/1.10/topics/db/models/#model-inheritance
    parent_post = models.ForeignKey(Post, related_name="comment_parent_post")
    author = models.ForeignKey(Author, related_name="comment_author")
    content = models.TextField(max_length=512)
    created_on = models.DateTimeField(auto_now=True)
    markdown = models.BooleanField()

    def get_absolute_url(self):
        """ Gets the canonical URL for a Post
        Will be of the format .../posts/<id>/comment/<id>
        """
        # This aint even in the user stories. Could skip???
        #return reverse('view_comment', args=[str(self.id)])

        # Redirects to previous list of comments with the anchor of the created post.
        #return reverse('list_comments_anchor', args=[str(self.parent_post.id), str(self.id)]).replace('%23', '#')
        return reverse('view_post', args=[str(self.parent_post.id)])

    def view_content(self):
        """ Retrieves content to be displayed as html, it is assumed safe
        due to HTMLsafe's get_converted_content() applies HTML escapes already.
        """
        return HTMLsafe.get_converted_content(self.markdown, self.content)

    # enable weird characters like lenny faces taken from:
    #http://stackoverflow.com/questions/36389723/why-is-django-using-ascii-instead-of-utf-8
    def __unicode__(self):
        return "Parent post:"+ str(self.parent_post.id) + ", Author:" + self.author.displayName + ": " + self.content

class ForeignCommentManager(models.Manager):
    """ Helps creating a foreign comment.
    """
    def create_comment(self, foreign_author, parent_post, content, contentType):
        markdown = False
        if contentType == "text/markdown" or contentType == "text/x-markdown":
            markdown = True
        c = ForeignComment.objects.create(foreign_author=foreign_author, parent_post=parent_post, content=content, markdown=markdown)
        return c

class ForeignCommentQuerySet(models.QuerySet):

    def all_foreign_comments_for_post(self, post_pk, ordered):
        # Retrieve only post specific comments
        results = self.filter(parent_post_id=post_pk)
        # Order it with latest date on top
        if(ordered):
            results = results.order_by('-created_on',)
        return results

class ForeignComment(models.Model):
    """ Represents a comment made by a foreign user
    Had to make another class because can't hide/override fields according to django when normal inheriting.
    https://docs.djangoproject.com/en/1.10/topics/db/models/#field-name-hiding-is-not-permitted
    """
    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    objects = CommentQuerySet.as_manager()
    parent_post = models.ForeignKey(Post, related_name="foreign_comment_parent_post")
    foreign_author = models.ForeignKey(ForeignAuthor, related_name="foreign_comment_author")
    content = models.TextField(max_length=512)
    created_on = models.DateTimeField(auto_now=True)
    markdown = models.BooleanField()

    def get_absolute_url(self):
        """ Gets the canonical URL for a Post
        Will be of the format .../posts/<id>/comment/<id>
        """
        return reverse('view_remote_post', args=[str(self.foreign_author.node.id), str(self.parent_post.id)])

    def view_content(self):
        """ Retrieves content to be displayed as html, it is assumed safe
        due to HTMLsafe's get_converted_content() applies HTML escapes already.
        """
        return HTMLsafe.get_converted_content(self.markdown, self.content)

    # enable weird characters like lenny faces taken from:
    #http://stackoverflow.com/questions/36389723/why-is-django-using-ascii-instead-of-utf-8
    def __unicode__(self):
        return "Parent post:"+ str(self.parent_post.id) + ", Author:" + self.author.displayName + ": " + self.content

class ImageManager(models.Manager):
    """ Helps creating an image object.
    Taken from https://docs.djangoproject.com/en/1.10/ref/models/instances/#creating-objects
    """
    def create_image(self, img, au, pst, imgtyp):
        img = self.create(image=img, author=au, parent_post=pst, imagetype=imgtyp)
        return img

class ImageServ(models.Model):
    """ Represents an image uploaded by the user. """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(Author, related_name="image_author")
    parent_post = models.ForeignKey(Post, related_name="image_parent_post")
    created_on = models.DateTimeField(auto_now=True)
    imagetype = models.CharField(max_length=12)
    image = models.BinaryField()
    objects = ImageManager()

    def ImageServ(self, image, author, parent_post, imagetype):
        self.image = image
        self.author = author
        self.parent_post = parent_post
        self.imagetype = imagetype

    def get_absolute_url(self):
        """ Gets the canonical URL for an image.
        Will be of the format .../images/<id>/comment/<id>
        """
        return reverse('view_image', args=[str(self.image)])

    def __unicode__(self):
        return self.author.displayName + ", created on " + str(self.created_on) +"  image type: " + str(self.imagetype)

class AdminConfig(models.Model):
    url = models.URLField()
    sharePosts = models.BooleanField(default=True, verbose_name="Share Posts with Other Nodes")
    shareImages = models.BooleanField(default=True, verbose_name="Share Images with Other Nodes")

    def __unicode__(self):
        return u"Admin Configuration"

    class Meta:
        verbose_name = "Admin Configuration"
        verbose_name_plural = "Admin Configuration"
