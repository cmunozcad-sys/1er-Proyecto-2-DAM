import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;


public class Validador {

    static final String CABECERA =
            "referencia,cliente,modelo,color,personalizacion,texto_bordado,logo_club,talla,cantidad";
    static final int COLUMNAS = 9;

    public static void main(String[] args) throws IOException {

        List<String> lineas = Files.readAllLines(Path.of("datos/ficha_fabricacion.csv"));

        if (lineas.isEmpty()) {
            System.out.println("ERROR: el fichero está vacío");
            System.exit(1);
        }

        String cabecera = lineas.get(0).replace("\"", "");
        if (!cabecera.equals(CABECERA)) {
            System.out.println("ERROR: la cabecera no es la esperada");
            System.exit(1);
        }

        if (lineas.size() == 1) {
            System.out.println("ERROR: el fichero no tiene líneas de pedido");
            System.exit(1);
        }

        int errores = 0;

        for (int i = 1; i < lineas.size(); i++) {
            int numeroLinea = i + 1;
            String[] columnas = partir(lineas.get(i));

            if (columnas.length != COLUMNAS) {
                System.out.println("ERROR línea " + numeroLinea + ": tiene " + columnas.length
                        + " columnas y debe tener " + COLUMNAS);
                errores++;
                continue;
            }

            if (columnas[0].isEmpty() || columnas[1].isEmpty() || columnas[2].isEmpty()) {
                System.out.println("ERROR línea " + numeroLinea + ": falta la referencia, el cliente o el modelo");
                errores++;
            }

            try {
                double talla = Double.parseDouble(columnas[7]);
                if (talla < 30 || talla > 48) {
                    System.out.println("ERROR línea " + numeroLinea + ": la talla " + columnas[7]
                            + " está fuera de rango (30-48)");
                    errores++;
                }
            } catch (NumberFormatException e) {
                System.out.println("ERROR línea " + numeroLinea + ": la talla '" + columnas[7] + "' no es un número");
                errores++;
            }

            try {
                int cantidad = Integer.parseInt(columnas[8]);
                if (cantidad <= 0) {
                    System.out.println("ERROR línea " + numeroLinea + ": la cantidad debe ser mayor que 0");
                    errores++;
                }
            } catch (NumberFormatException e) {
                System.out.println("ERROR línea " + numeroLinea + ": la cantidad '" + columnas[8]
                        + "' no es un número entero");
                errores++;
            }
        }

        if (errores > 0) {
            System.out.println("Validación fallida: " + errores + " error(es)");
            System.exit(2);
        }

        System.out.println("OK: " + (lineas.size() - 1) + " líneas de pedido correctas");
        System.exit(0);
    }

    static String[] partir(String linea) {
        List<String> columnas = new ArrayList<>();
        StringBuilder actual = new StringBuilder();
        boolean entreComillas = false;

        for (char c : linea.toCharArray()) {
            if (c == '"') {
                entreComillas = !entreComillas;
            } else if (c == ',' && !entreComillas) {
                columnas.add(actual.toString().trim());
                actual.setLength(0);
            } else {
                actual.append(c);
            }
        }
        columnas.add(actual.toString().trim());

        return columnas.toArray(new String[0]);
    }
}