interface TagProps {
  label: string;
  color?: string;
}

const Tag = ({ label, color }: TagProps) => {
  return (
    <span
      className={`inline-block px-2 py-0.5 text-xs font-medium rounded-md ${
        color || "bg-gray-100 text-gray-800"
      }`}
    >
      {label}
    </span>
  );
};

export { Tag }
