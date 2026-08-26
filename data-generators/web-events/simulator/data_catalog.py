"""Synthetic catalog used until the project has a transactional database.

The IDs are intentionally fictitious. The module centralizes the catalog so that the
same product always keeps the same category and price across product_view,
add_to_cart, purchase and other events.
"""

from dataclasses import dataclass
import random
from typing import Iterable


@dataclass(frozen=True)
class Category:
    category_id: str
    name: str


@dataclass(frozen=True)
class Product:
    product_id: str
    category_id: str
    name: str
    unit_price: int


class DataCatalog:
    """In-memory synthetic catalog with deterministic IDs and coherent relationships."""

    def __init__(self) -> None:
        self.categories = [
            Category("cat_001", "tecnologia"),
            Category("cat_002", "hogar"),
            Category("cat_003", "deportes"),
            Category("cat_004", "moda"),
            Category("cat_005", "belleza"),
        ]

        product_seed = {
            "cat_001": [
                ("audifonos bluetooth", 129900),
                ("teclado mecanico", 249900),
                ("mouse inalambrico", 89900),
                ("monitor 24 pulgadas", 699900),
                ("portatil 14 pulgadas", 2499900),
                ("cargador usb c", 79900),
                ("webcam full hd", 189900),
                ("parlante bluetooth", 219900),
            ],
            "cat_002": [
                ("cafetera", 189900),
                ("licuadora", 249900),
                ("juego de sartenes", 319900),
                ("lampara de mesa", 119900),
                ("aspiradora", 649900),
                ("organizador", 69900),
                ("almohada", 89900),
                ("vajilla", 229900),
            ],
            "cat_003": [
                ("balon de futbol", 109900),
                ("mancuernas", 199900),
                ("tapete de yoga", 89900),
                ("termo deportivo", 69900),
                ("guantes de entrenamiento", 79900),
                ("banda elastica", 49900),
                ("morral deportivo", 159900),
                ("cuerda para saltar", 39900),
            ],
            "cat_004": [
                ("camiseta basica", 69900),
                ("jean", 159900),
                ("tenis casuales", 249900),
                ("chaqueta", 289900),
                ("gorra", 59900),
                ("buzo", 139900),
                ("pantalon", 149900),
                ("camisa", 119900),
            ],
            "cat_005": [
                ("perfume", 279900),
                ("crema facial", 119900),
                ("protector solar", 89900),
                ("shampoo", 59900),
                ("secador de cabello", 239900),
                ("kit de cuidado personal", 169900),
                ("serum facial", 129900),
                ("cepillo electrico", 179900),
            ],
        }

        self.products: list[Product] = []
        product_number = 1
        for category in self.categories:
            for name, price in product_seed[category.category_id]:
                self.products.append(
                    Product(
                        product_id=f"prod_{product_number:04d}",
                        category_id=category.category_id,
                        name=name,
                        unit_price=price,
                    )
                )
                product_number += 1

        self._products_by_id = {p.product_id: p for p in self.products}
        self._products_by_category: dict[str, list[Product]] = {
            c.category_id: [p for p in self.products if p.category_id == c.category_id]
            for c in self.categories
        }

    def random_category(self, rng: random.Random) -> Category:
        return rng.choice(self.categories)

    def random_product(self, rng: random.Random, category_id: str | None = None) -> Product:
        candidates = self._products_by_category[category_id] if category_id else self.products
        return rng.choice(candidates)

    def product(self, product_id: str) -> Product:
        return self._products_by_id[product_id]

    def products_for_category(self, category_id: str) -> Iterable[Product]:
        return tuple(self._products_by_category[category_id])

    def search_query_for_product(self, product: Product) -> str:
        return product.name

    @staticmethod
    def no_results_query(rng: random.Random) -> str:
        # Deliberately synthetic queries that do not match the in-memory catalog.
        return rng.choice(
            [
                "consola retro transparente edicion lunar",
                "zapatillas anfibias talla especial",
                "cafetera holografica portatil",
                "reloj solar de escritorio inteligente",
                "audifonos sumergibles profesionales",
            ]
        )
