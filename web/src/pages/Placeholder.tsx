import Card from "../components/Card";

export default function Placeholder({ title, brick }: { title: string; brick: number }) {
  return (
    <>
      <h1 className="mb-6 text-2xl font-semibold">{title}</h1>
      <Card>
        <p className="text-slate-500">Cette section arrive avec la brique {brick}.</p>
      </Card>
    </>
  );
}
