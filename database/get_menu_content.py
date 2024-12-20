from aiogram.types import InputMediaPhoto
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import Session

from database.models import Orders
from database.orm_query import (
    orm_add_to_cart,
    orm_delete_from_cart,
    orm_get_banner,
    orm_get_categories,
    orm_get_products,
    orm_get_user_cart,
    orm_get_user_orders,
)
from kbds.inline import (
    get_products_btns,
    get_user_cart,
    get_user_catalog_btns,
    get_user_main_btns,
    get_user_orders,
)

from utils.paginator import Paginator

async def main_menu(session, level, menu_name):
    banner = await orm_get_banner(session, menu_name)
    if not banner:
        return None, None

    image = InputMediaPhoto(media=banner.image, caption=banner.description)
    kbds = get_user_main_btns(level=level)
    return image, kbds

async def catalog(session, level, menu_name):
    banner = await orm_get_banner(session, menu_name)
    if not banner:
        return None, None

    image = InputMediaPhoto(media=banner.image, caption=banner.description)
    categories = await orm_get_categories(session)
    kbds = get_user_catalog_btns(level=level, categories=categories)
    return image, kbds

def pages(paginator: Paginator):
    btns = dict()
    if paginator.has_previous():
        btns["◀ Попер."] = "previous"
    if paginator.has_next():
        btns["Слід. ▶"] = "next"
    return btns

async def products(session, level, category, page):
    products = await orm_get_products(session, category_id=category)
    paginator = Paginator(products, page=page)
    product = paginator.get_page()[0]

    image = InputMediaPhoto(
        media=product.image,
        caption=(f"<strong>{product.name}</strong>\n{product.description}"
                 f"\nВартість: {round(product.price, 2)}"
                 f"\n<strong>Продукт {paginator.page} з {paginator.pages}</strong>")
    )

    pagination_btns = pages(paginator)
    kbds = get_products_btns(
        level=level,
        category=category,
        page=page,
        pagination_btns=pagination_btns,
        product_id=product.id,
    )
    return image, kbds

async def carts(session, level, menu_name, page, user_id, product_id):
    if menu_name == "delete":
        await orm_delete_from_cart(session, user_id, product_id)
        if page > 1:
            page -= 1
    elif menu_name == "decrement":
        is_cart = await orm_reduce_product_in_cart(session, user_id, product_id)
        if page > 1 and not is_cart:
            page -= 1
    elif menu_name == "increment":
        await orm_add_to_cart(session, user_id, product_id)

    carts = await orm_get_user_cart(session, user_id)
    if not carts:
        banner = await orm_get_banner(session, "cart")
        if not banner:
            return None, None

        image = InputMediaPhoto(
            media=banner.image,
            caption=f"<strong>{banner.description}</strong>"
        )
        kbds = get_user_cart(
            level=level,
            page=None,
            pagination_btns=None,
            product_id=None,
        )
    else:
        paginator = Paginator(carts, page=page)
        cart = paginator.get_page()[0]

        cart_price = round(cart.quantity * cart.product.price, 2)
        total_price = round(sum(cart.quantity * cart.product.price for cart in carts), 2)
        image = InputMediaPhoto(
            media=cart.product.image,
            caption=(f"<strong>{cart.product.name}</strong>"
                     f"\n{cart.product.price}$ x {cart.quantity} = {cart_price}$"
                     f"\nПродукт {paginator.page} з {paginator.pages} в кошику."
                     f"\nЗагальна вартість товарів у кошику {total_price}")
        )

        pagination_btns = pages(paginator)
        kbds = get_user_cart(
            level=level,
            page=page,
            pagination_btns=pagination_btns,
            product_id=cart.product.id,
        )
    return image, kbds


# async def orders(session: Session, level: int, user_id: int, product_id: int) -> object:
#     query = select(Orders).where(Orders.user_id == user_id).order_by(Order.created_at.desc())
#     result = await session.execute(query)
#     orders_list = result.scalars().all()
#
#     if not orders_list:
#         banner = await orm_get_banner(session, "orders")
#         if not banner:
#             return None, None
#
#         image = InputMediaPhoto(
#             media=banner.image,
#             caption=f"<strong>{banner.description}</strong>"
#         )
#         kbds = get_user_cart(
#             level=level,
#             page=None,
#             pagination_btns=None,
#             product_id=None,
#         )
#     else:
#         paginator = Paginator(orders, page=page)
#         order = paginator.get_page()[0]
#
#         order_price = round(order.quantity * order.product.price, 2)
#         total_price = round(sum(order.quantity * order.product.price for order in carts), 2)
#         image = InputMediaPhoto(
#             media=order.product.image,
#             caption=(f"<strong>{order.product.name}</strong>"
#                      f"\n{order.product.price}$ x {order.quantity} = {order_price}$"
#                      f"\nПродукти {paginator.pages} в кошику."
#                      f"\nЗагальна вартість товарів у кошику {total_price}")
#         )
#
#     message_text = "Ваші замовлення:\n\n"
#     for order in orders_list:
#         message_text += f"Замовлення №{order.id} - {order.total_price}$ ({order.created_at.strftime('%Y-%m-%d')})\n"
#
#     # Створити кнопки для взаємодії
#     kbds = InlineKeyboardBuilder()
#     kb.add(InlineKeyboardButton(text="На головну", callback_data="main_menu"))
#     return image, kbds


async def my_orders(session, level, menu_name, user_id, page):
    # Отримати список замовлень користувача, сортування за датою
    query = select(Orders).where(Orders.user_id == user_id).order_by(Orders.created.desc())
    result = await session.execute(query)
    orders_list = result.scalars().all()

    # Якщо замовлень немає, відобразити повідомлення з банером
    if not orders_list:
        banner = await orm_get_banner(session, "orders")
        if not banner:
            return (
                None,
                "У вас немає замовлень. Ви можете зробити замовлення у нашому магазині!",
                InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="На головну", callback_data="main_menu")]
                    ]
                ),
            )

        image = InputMediaPhoto(
            media=banner.image,
            caption=f"<strong>{banner.description}</strong>"
        )
        kbds = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="На головну", callback_data="main_menu")]]
        )
        return image, kbds

    # Використовуємо пагінацію, якщо є багато замовлень
    paginator = Paginator(orders_list, page=page)
    current_order = paginator.get_page()[0]

    # Формуємо текст із замовленням
    message_text = "Ваші замовлення:\n\n"
    for order in paginator.get_page():
        message_text += f"Замовлення №{order.id} - {order.total_price}$ ({order.created.strftime('%Y-%m-%d')})\n"

    # Деталі замовлення, якщо потрібні зображення продукту
    # image = (
    #     # media=current_order.product.image,  # Перевірте, чи продукт має атрибут `image`
    #     caption=f"<strong>Замовлення №{current_order.id}</strong>\n"
    #             f"Загальна сума: {current_order.total_price}$\n"
    #             f"Дата: {current_order.created.strftime('%Y-%m-%d')}"
    # )

    # Кнопки для пагінації або повернення до головного меню
    kbds = InlineKeyboardMarkup(inline_keyboard=[])
    if paginator.has_previous:
        kbds.inline_keyboard.append(
            [InlineKeyboardButton(text="⬅️ Попередня", callback_data=f"orders_page_{page - 1}")]
        )
    if paginator.has_next:
        kbds.inline_keyboard.append(
            [InlineKeyboardButton(text="➡️ Наступна", callback_data=f"orders_page_{page + 1}")]
        )
    kbds.inline_keyboard.append(
        [InlineKeyboardButton(text="На головну", callback_data="main_menu")]
    )

    return image, message_text, kbds


async def get_menu_content(
    session: AsyncSession,
    level: int,
    menu_name: str,
    category: int | None = None,
    page: int | None = None,
    product_id: int | None = None,
    user_id: int | None = None,
):
    if level == 0:
        return await main_menu(session, level, menu_name)
    elif level == 1:
        return await catalog(session, level, menu_name)
    elif level == 2:
        return await products(session, level, category, page)
    elif level == 3:
        return await carts(session, level, menu_name, page, user_id, product_id)
    elif level == 4:
        return await my_orders(session, level, menu_name, user_id, page=0)