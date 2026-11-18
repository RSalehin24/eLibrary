import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { BookProcessingProvider } from "./features/processing/BookProcessingStore";
import { SessionProvider } from "./hooks/useSession";
import { bootstrapTheme } from "./hooks/useTheme";
import { ToastProvider } from "./hooks/useToast";
import "./styles/app.css";

bootstrapTheme();

ReactDOM.createRoot(document.getElementById("root")).render(
  <BrowserRouter>
    <SessionProvider>
      <ToastProvider>
        <BookProcessingProvider>
          <App />
        </BookProcessingProvider>
      </ToastProvider>
    </SessionProvider>
  </BrowserRouter>,
);
