"""
This module contains pytest fixtures and test cases to ensure the
integrity of CRUD operations, search functionality, and filtering.
"""
import os
from typing import Generator, List, Callable, Union

import pytest
from flask.testing import FlaskClient

from app import app, db, Book

os.environ["FLASK_ENV"] = "testing"
app.config["WTF_CSRF_ENABLED"] = False


@pytest.fixture
def client() -> Generator[FlaskClient, None, None]:
    """
    Sets up the database in memory for each test case.

    Yields:
        FlaskClient: the test client for the Flask application.
    """
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


@pytest.fixture
def create_books() -> Callable[[int], Union[List[Book], Book]]:
    """
    Fixture to create the specified number of books for each test case.

    Returns:
        get_books(n) function that takes 'n' (int) and returns a list of created Book objects.
    """

    def books(n: int = 1) -> Union[List[Book], Book]:
        books_list = []
        for i in range(n):
            books_list.append(Book(
                title=f"Book Title {i + 1}",
                author=f"Author {i + 1}",
                year=1995 + i,
                genre=f"other"
            ))
        db.session.add_all(books_list)
        db.session.commit()
        return books_list[0] if len(books_list) == 1 else books_list

    return books


def test_list_books(client: FlaskClient) -> None:
    """Tests if the list page loads correctly."""
    book = Book(title="List Test", author="Author")
    db.session.add(book)
    db.session.commit()

    response = client.get("/")
    assert response.status_code == 200
    assert b"List Test" in response.data


def test_add_book(client: FlaskClient) -> None:
    """Tests the addition of a new book."""
    response = client.post("/add", data={
        "title": "Test Book",
        "author": "Test Author",
        "year": 2023,
        "genre": "romance",
        "submit": True
    }, follow_redirects=True)

    assert response.status_code == 200
    book = Book.query.filter_by(title="Test Book").first()

    assert book is not None
    assert book.author == "Test Author"
    assert book.genre == "romance"


def test_edit_book(client: FlaskClient, create_books: Callable) -> None:
    """Tests the editing of the book."""
    test_book = create_books()
    response = client.post(
        f'/edit/{test_book.id}',
        data={
            "title": "Updated Title",
            "author": "Updated Author",
            "year": 2025,
            "genre": "science fiction",
            "submit": True
        },
        follow_redirects=True
    )

    assert response.status_code == 200
    edited_book = Book.query.get(test_book.id)

    assert edited_book.title == "Updated Title"
    assert edited_book.author == "Updated Author"
    assert edited_book.year == 2025
    assert edited_book.genre == "science fiction"


def test_delete_book(client: FlaskClient, create_books: Callable) -> None:
    """Tests the removing of the book."""
    test_book = create_books()
    response = client.post(
        f'/delete/{test_book.id}',
        follow_redirects=True
    )
    assert response.status_code == 200
    deleted_book = Book.query.get(test_book.id)
    assert deleted_book is None


def test_search_book(client: FlaskClient, create_books: Callable) -> None:
    """Tests searching for books by title or author."""
    create_books(2)
    response_1 = client.get("/?q=title+1")
    assert response_1.status_code == 200
    assert b"Book Title 1" in response_1.data

    response_2 = client.get("/?q=author+2")
    assert response_2.status_code == 200
    assert b"Book Title 2" in response_2.data
    assert b"Author 2" in response_2.data


def test_filter_by_genre(client: FlaskClient, create_books: Callable) -> None:
    """Tests filtering books by genre."""
    test_books = create_books(3)
    client.post(
        f'/edit/{test_books[0].id}',
        data={
            "genre": "science fiction",
            "submit": True
        },
        follow_redirects=True
    )

    response = client.get("/?genre=science+fiction")
    assert response.status_code == 200
    assert b"Book Title 1" in response.data
    assert b"Book Title 2" not in response.data
    assert b"Book Title 3" not in response.data
