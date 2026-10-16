"use client";

export default function ErrorPage({ reset }: { reset: () => void }) {
  return <section className="empty-state" role="alert"><h1>এই মুহূর্তে তথ্য পাওয়া যাচ্ছে না</h1>
    <p>সংযোগ পরীক্ষা করে আবার চেষ্টা করুন।</p><button className="button" onClick={reset}>আবার চেষ্টা করুন</button></section>;
}
