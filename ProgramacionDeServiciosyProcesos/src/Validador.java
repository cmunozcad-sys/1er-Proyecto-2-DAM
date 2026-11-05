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

        System.out.println("OK: formato correcto, " + (lineas.size() - 1) + " líneas de pedido");
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