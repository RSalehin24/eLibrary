import { addBookToMyBooks, removeBookFromMyBooks } from "../../../api/catalog";
import { useAsyncAction } from "../../../hooks/useAsyncAction";

export function useBookOwnershipActions({ book, setBook, slug, toast }) {
  const action = useAsyncAction();

  async function toggleMyBooks() {
    if (!book) {
      return;
    }
    await action.run("my-books", async () => {
      if (book.is_in_my_books) {
        await removeBookFromMyBooks(slug);
        setBook((current) => ({
          ...current,
          is_in_my_books: false,
          my_books_added_at: null,
        }));
        toast.success("Removed from My Books.");
        return;
      }
      const payload = await addBookToMyBooks(slug);
      setBook((current) => ({
        ...current,
        is_in_my_books: true,
        my_books_added_at: payload.my_books_added_at,
      }));
      toast.success("Added to My Books.");
    }).catch((nextError) => toast.error(nextError.message));
  }

  return {
    togglingMyBooks: action.pending,
    toggleMyBooks,
  };
}
