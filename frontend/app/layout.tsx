export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <head>
        <title>Budget Famille</title>
        <meta name="description" content="Gestion budgétaire familiale sécurisée" />
      </head>
      <body>
        {children}
      </body>
    </html>
  );
}