import { addBookToMyBooks, removeBookFromMyBooks } from "../../api/catalog";
import { useAsyncAction } from "../../hooks/useAsyncAction";

export function useMyBooksAction({ toast, updateEntry }) {
  const action = useAsyncAction();

  async function toggleMyBooks(book) {
    await action.run(book.id, async () => {
      if (book.is_in_my_books) {
        await removeBookFromMyBooks(book.slug);
        updateEntry(book.id, { is_in_my_books: false, my_books_added_at: null });
        toast.success("Removed from My Books.");
        return;
      }

      const payload = await addBookToMyBooks(book.slug);
      updateEntry(book.id, {
        is_in_my_books: true,
        my_books_added_at: payload.my_books_added_at,
      });
      toast.success("Added to My Books.");
    }).catch((nextError) => toast.error(nextError.message));
  }

  return {
    busyIds: { [action.pendingKey]: true },
    toggleMyBooks,
  };
}
