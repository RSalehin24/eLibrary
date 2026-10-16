export const metadata = { title: "যোগাযোগ", alternates: { canonical: "/contact/" },
  description: "বইয়ের তথ্যে ভুল বা অ্যাকাউন্টের সমস্যা সম্পর্কে পাঠাগারের পরিচালকের সঙ্গে যোগাযোগের নির্দেশনা।" };

export default function ContactPage() {
  const email = process.env.PUBLIC_CONTACT_EMAIL;
  return <article className="article"><p className="eyebrow">আপনার মতামত</p><h1>যোগাযোগ</h1>
    <p>বইয়ের তথ্যে কোনো ভুল দেখলে বইয়ের নাম, ক্যাটালগ নম্বর এবং সংশোধনের নির্ভরযোগ্য উৎস উল্লেখ করুন। অ্যাকাউন্টের সমস্যা জানাতে কোন পাতায় কী সমস্যা হচ্ছে তা লিখুন।</p>
    {email ? <p>পাঠাগারের পরিচালকের ইমেইল: <a className="text-link" href={`mailto:${email}`}>{email}</a></p>
      : <p>অ্যাকাউন্টের আমন্ত্রণ যিনি পাঠিয়েছেন, তাঁর সঙ্গে যোগাযোগ করুন।</p>}
    <p>যোগাযোগের বার্তায় পাসওয়ার্ড বা দুই ধাপের যাচাইয়ের কোড পাঠাবেন না।</p>
  </article>;
}
