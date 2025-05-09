const InitialAvatar = ({ username }: { username: string }) => {
  const initials = username
    .split(/[\s._-]+/) // split by space, dot, underscore, dash
    .filter(Boolean)   // hilangkan elemen kosong
    .map((n) => n[0]?.toUpperCase()) // ambil huruf pertama dan kapital
    .slice(0, 2) // ambil maksimal 2 huruf
    .join("");

  return (
    <div className="w-10 h-10 rounded-full bg-primary text-white flex items-center justify-center font-bold">
      {initials || "?"}
    </div>
  );

}

export { InitialAvatar }
