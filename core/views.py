from django.db.models import Q
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, View
from django.shortcuts import redirect
from django.utils import timezone
from .forms import CheckoutForm,  CouponForm
from .models import Item, OrderItem, Order, BillingAddress, Payment, Coupon, Profile, Category

import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY 


# Create your views here.
def products(request):
    context= {
        'items': Item.objects.all()
    }
    return render(request, "product.html", context)

class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            form = CheckoutForm()
            context = {
                'form': form,
                'couponform': CouponForm(),
                'order': order,
                'DISPLAY_COUPON_FORM': True
            }
            return render(self.request, "checkout.html", context)       
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order.")      
            return redirect("core:checkout")
           

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        order = Order.objects.get(user=self.request.user, ordered=False)
        try:
            if form.is_valid():
                street_address = form.cleaned_data.get('street_address')
                apartment_address = form.cleaned_data.get('apartment_address' )
                country = form.cleaned_data.get('country')
                zip = form.cleaned_data.get('zip')
              
                payment_option = form.cleaned_data.get('payment_option')
                billing_address = BillingAddress(
                    user=self.request.user,
                    street_address=street_address,
                    apartment_address=apartment_address,
                    country=country,
                    zip=zip
                )
                billing_address.save()
                order.billing_address = billing_address
                order.save()
                
                if payment_option == "S":
                    return redirect('core:payment', payment_option="stripe")
                elif payment_option == "P":
                    return redirect('core:payment', payment_option="paypal")
                else:
                    messages.warning(self.request, "Invalid Payment Option")
                    return redirect('core:checkout')
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("core:order-summary")

class PaymentView(View):
    def get(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        if order.billing_address:
            context = {
                'order': order,
                'DISPLAY_COUPON_FORM': False
            }
            return render(self.request, "payment.html", context)
        else:
            messages.warning(self.request, "You have not added a billing address")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        token = self.request.POST.get('stripeToken')
        amount = int(order.get_total() * 100)
        try:
            charge = stripe.Charge.create(
                amount=amount,
                currency="usd",
                source=token
            )
            payment = Payment()
            payment.stripe_charge_id = charge['id']
            payment.user = self.request.user
            payment.amount = order.get_total()
            payment.save()

            order_items = order.items.all()
            order_items.update(ordered=True)
            for item in order_items:
                item.save()

            order.ordered=True
            order.payment = payment
            order.save()
            messages.success(self.request, "Your order was successful!")
            return redirect("/")

        except stripe.error.CardError as e:
            # Since it's a decline, stripe.error.CardError will be caught
            body = e.json_body
            err  = body.get('error', {})
            messages.warning(self.request, f"{err.get('message')}")
            return redirect("/")
        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            messages.warning(self.request, f"{err.get('RateLimitError')}")
            return redirect("/")
        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            messages.warning(self.request, f"{err.get('Invalid Parameters')}")
            return redirect("/")
        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            messages.warning(self.request, f"{err.get('Authentication Error')}")
            return redirect("/")
        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            messages.warning(self.request, f"{err.get('Network Error')}")
            return redirect("/")
        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            messages.warning(self.request, f"{err.get('Something went wrong. You were not charged.')}")
            return redirect("/")
        except Exception as e:
            # Something else happened, completely unrelated to Stripe
            messages.warning(self.request, f"{err.get('A serious error has occured. We have been notified.')}")
            return redirect("/")

      
def get_category():
    queryset = Item.objects.values('categories__title')
    return queryset

       
def home(request):
    latest = Item.objects.order_by('-date')[0:4]
    category = get_category()
    all_categories = Category.objects.all()
    queryset = Item.objects.filter(featured=True)

    context = {
        'latest': latest,
        'category': category,
        'all_categories': all_categories,
        'object_list' : queryset
    }
    return render(request, "home-page.html", context)

def category_profile(request, id):
    one_category = get_object_or_404(Category, id=id)
    cat_queryset = Item.objects.all()
    cat_query = one_category.title
    cat_queryset = cat_queryset.filter(Q(categories__title__icontains=cat_query)).distinct()
    context = {
        'one_category': one_category,
        'queryset': cat_queryset
     }

    return render(request, "category_profile.html", context)

# def profile(request, id):
#     user_prof = get_object_or_404(Profile, id=id)
#     prof_queryset = Item.objects.all()
#     prof_query = 

# class HomeView(View):
#     model = Item
#     paginate_by = 4
#     template_name = "home-page.html"

class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order
            }
            return render(self.request, "order_summary.html", context)
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("/")

        

class ItemDetailView(DetailView):
    model = Item
    template_name = "product.html"

class ProfileView(DetailView):
    model = Order
    template_name = "profile.html"

@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
        )
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        #check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
           order_item.quantity += 1
           order_item.save()
           messages.info(request, "This item was updated to your cart")  
           return redirect("core:order-summary") 
        else:
           messages.info(request, "This item was added to your cart")  
           order.items.add(order_item)
           return redirect("core:order-summary")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "This item was added to your cart")  
        return redirect("core:order-summary")

@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        #check if the order item is in the order
        if  order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
                )[0]
            order.items.remove(order_item)
            messages.info(request, "This item was removed from your cart")      
            return redirect("core:order-summary")
        else: 
            messages.info(request, "This item was not in your cart")  
            return redirect("core:product", slug=slug) 
    else:
        #add message saying user doesnt have an order
        messages.info(request, "You do not have an active order")  
        return redirect("core:product", slug=slug)

@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        #check if the order item is in the order
        if  order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
                )[0]
            if order_item.quantity >1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request, "This item was quantity was updated")      
            return redirect("core:order-summary")
        else: 
            messages.info(request, "This item was not in your cart")  
            return redirect("core:order-summary") 
    else:
        #add message saying user doesnt have an order
        messages.info(request, "You do not have an active order")  
        return redirect("core:order-summary")

def get_coupon(request, code):
    try:
      coupon = Coupon.objects.get(code=code)
      return coupon
    except ObjectDoesNotExist:
      messages.info(request, "This coupon does not exist.")      
      return redirect("core:checkout")

class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                order = Order.objects.get(user=self.request.user, ordered=False)
                order.coupon = get_coupon(self.request, code)
                order.save()
                messages.success(self.request, "Successfully added coupon.")      
                return redirect("core:checkout")
            except ObjectDoesNotExist:
                messages.info(self.request, "You do not have an active order.")      
                return redirect("core:checkout")

# def profile(request, user):
    
#     profile = get_object_or_404(Order,  user=request.user)
#     order_qs = Order.objects.filter(user=request.user, ordered=False)
#     try:
#         profile_info = Profile.get_profile(profile.id)
#     except:
#         profile_info = Profile.filter_by_id(profile.id)
#     context = {
#         'profile' : profile,
#         'profile_info' : profile_info
#          }
#     return render(self.request, "profile.html", context)  